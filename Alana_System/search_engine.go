package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/qdrant/go-client/qdrant"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

// ==============================
// Domain & Config
// ==============================

type SearchResult struct {
	Text  string
	Page  int
	Score float32
}

type Config struct {
	SidecarURL     string
	QdrantHost     string
	QdrantPort     int
	SearchTimeout  time.Duration
	ContextTokens  int
	ScoreThreshold float32
}

func loadConfig() Config {
	searchTimeout, _ := strconv.Atoi(getEnv("SEARCH_TIMEOUT_SEC", "15"))
	tokens, _ := strconv.Atoi(getEnv("CONTEXT_TOKENS", "3000"))
	threshold, _ := strconv.ParseFloat(getEnv("SCORE_THRESHOLD", "0.3"), 32)
	qdrantPort, _ := strconv.Atoi(getEnv("QDRANT_PORT", "6334"))

	return Config{
		SidecarURL:     getEnv("PYTHON_SIDECAR_URL", "http://127.0.0.1:8000"),
		QdrantHost:     getEnv("QDRANT_HOST", "127.0.0.1"),
		QdrantPort:     qdrantPort,
		SearchTimeout:  time.Duration(searchTimeout) * time.Second,
		ContextTokens:  tokens,
		ScoreThreshold: float32(threshold),
	}
}

func getEnv(key, fallback string) string {
	if value, ok := os.LookupEnv(key); ok {
		return value
	}
	return fallback
}

// ==============================
// Python Sidecar Client (with Retries)
// ==============================

type EmbedRequest struct {
	Text string `json:"text"`
}

type EmbedResponse struct {
	Vector []float32 `json:"vector"`
}

type GenerateRequest struct {
	Query   string `json:"query"`
	Context string `json:"context"`
}

type GenerateResponse struct {
	Answer string `json:"answer"`
}

func callSidecar(ctx context.Context, endpoint string, payload interface{}, target interface{}) error {
	body, err := json.Marshal(payload)
	if err != nil {
		return err
	}

	// Retry logic (3 attempts)
	var lastErr error
	for i := 0; i < 3; i++ {
		if i > 0 {
			time.Sleep(time.Duration(i) * time.Second)
			log.Printf("🔄 Tentativa %d para %s...", i+1, endpoint)
		}

		req, err := http.NewRequestWithContext(ctx, http.MethodPost, endpoint, bytes.NewBuffer(body))
		if err != nil {
			return err
		}
		req.Header.Set("Content-Type", "application/json")

		resp, err := http.DefaultClient.Do(req)
		if err != nil {
			lastErr = err
			continue
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			raw, _ := io.ReadAll(resp.Body)
			lastErr = fmt.Errorf("API error (%d): %s", resp.StatusCode, string(raw))
			continue
		}

		return json.NewDecoder(resp.Body).Decode(target)
	}
	return fmt.Errorf("falha após 3 tentativas: %w", lastErr)
}

// ==============================
// Search Engine (Qdrant)
// ==============================

type AlanaEngine struct {
	config Config
}

func (e *AlanaEngine) Search(ctx context.Context, vector []float32, topK uint64) ([]SearchResult, error) {
	ctx, cancel := context.WithTimeout(ctx, e.config.SearchTimeout)
	defer cancel()

	address := fmt.Sprintf("%s:%d", e.config.QdrantHost, e.config.QdrantPort)
	conn, err := grpc.DialContext(ctx, address, grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		return nil, fmt.Errorf("falha ao conectar no Qdrant (%s): %w", address, err)
	}
	defer conn.Close()

	pointsClient := qdrant.NewPointsClient(conn)
	resp, err := pointsClient.Search(ctx, &qdrant.SearchPoints{
		CollectionName: "alana_knowledge_base",
		Vector:         vector,
		Limit:          topK,
		WithPayload: &qdrant.WithPayloadSelector{
			SelectorOptions: &qdrant.WithPayloadSelector_Enable{Enable: true},
		},
		ScoreThreshold: &e.config.ScoreThreshold,
	})
	if err != nil {
		return nil, fmt.Errorf("busca falhou: %w", err)
	}

	results := make([]SearchResult, 0, len(resp.GetResult()))
	for _, point := range resp.GetResult() {
		payload := point.GetPayload()
		text := ""
		if v, ok := payload["text"]; ok {
			text = v.GetStringValue()
		}
		page := 0
		if v, ok := payload["page_number"]; ok {
			page = int(v.GetIntegerValue())
		}
		results = append(results, SearchResult{
			Text:  text,
			Page:  page,
			Score: point.GetScore(),
		})
	}
	return results, nil
}

func (e *AlanaEngine) AssembleContext(results []SearchResult) string {
	charLimit := e.config.ContextTokens * 3
	var b strings.Builder
	b.WriteString("Contexto recuperado dos documentos:\n\n")

	for _, r := range results {
		block := fmt.Sprintf("--- [Fonte/Pág %d | Score %.2f] ---\n%s\n\n", r.Page, r.Score, r.Text)
		if b.Len()+len(block) > charLimit {
			b.WriteString("[Contexto truncado]")
			break
		}
		b.WriteString(block)
	}
	return b.String()
}

// ==============================
// Main
// ==============================

func main() {
	cfg := loadConfig()
	engine := &AlanaEngine{config: cfg}
	ctx := context.Background()

	fmt.Printf("🤖 Alana System | Qdrant: %s | API: %s\n", cfg.QdrantHost, cfg.SidecarURL)

	question := "Explique o funcionamento de um transistor NPN."
	if len(os.Args) > 1 {
		question = strings.Join(os.Args[1:], " ")
	}

	fmt.Printf("❓ Pergunta: %s\n", question)

	// Step 1: Embedding
	var embedOut EmbedResponse
	if err := callSidecar(ctx, cfg.SidecarURL+"/embed", EmbedRequest{Text: question}, &embedOut); err != nil {
		log.Printf("❌ Erro no embedding: %v", err)
		return
	}

	// Step 2: Search
	results, err := engine.Search(ctx, embedOut.Vector, 5)
	if err != nil {
		log.Printf("❌ Erro na busca: %v", err)
		return
	}
	fmt.Printf("🔍 Encontrados %d resultados no Qdrant.\n", len(results))

	// Step 3: Answer
	contextText := engine.AssembleContext(results)
	var genOut GenerateResponse
	if err := callSidecar(ctx, cfg.SidecarURL+"/generate", GenerateRequest{Query: question, Context: contextText}, &genOut); err != nil {
		log.Printf("❌ Erro na geração: %v", err)
		return
	}

	fmt.Println("\n✅ Resposta da Alana:")
	fmt.Println("----------------------------------------")
	fmt.Println(genOut.Answer)
	fmt.Println("----------------------------------------")
}