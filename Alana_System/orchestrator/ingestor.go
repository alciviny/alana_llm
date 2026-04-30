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
	"os/signal"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"syscall"
	"time"
)

// Task define a estrutura de uma tarefa de processamento.
type Task struct {
	Path string `json:"path"`
	Type string `json:"type"`
}

type Config struct {
	RawDir        string
	NumWorkers    int
	PythonSidecar string
	Timeout       time.Duration
}

func loadConfig() Config {
	workers, _ := strconv.Atoi(getEnv("INGESTION_WORKERS", "4"))
	timeout, _ := strconv.Atoi(getEnv("INGESTION_TIMEOUT_SEC", "300")) // 5 min default por doc

	sidecar := getEnv("PYTHON_SIDECAR_URL", "http://127.0.0.1:8000")
	if !bytes.HasSuffix([]byte(sidecar), []byte("/")) {
		sidecar += "/"
	}

	return Config{
		RawDir:        getEnv("RAW_DATA_DIR", "./data/raw"),
		NumWorkers:    workers,
		PythonSidecar: sidecar + "process_document",
		Timeout:       time.Duration(timeout) * time.Second,
	}
}

func getEnv(key, fallback string) string {
	if value, ok := os.LookupEnv(key); ok {
		return value
	}
	return fallback
}

func main() {
	cfg := loadConfig()
	fmt.Printf("🚀 Orquestrador Alana (Ingestor) Iniciado\n")
	fmt.Printf("📂 Diretório Alvo: %s | Workers: %d | API: %s\n", cfg.RawDir, cfg.NumWorkers, cfg.PythonSidecar)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// Captura Ctrl+C para cancelamento gracioso
	sig := make(chan os.Signal, 1)
	signal.Notify(sig, os.Interrupt, syscall.SIGTERM)
	go func() {
		<-sig
		fmt.Println("\n⛔ Sinal de interrupção recebido. Cancelando Workers...")
		cancel()
	}()

	tasks := make(chan Task, 100)
	var wg sync.WaitGroup

	// Inicia os workers
	for i := 1; i <= cfg.NumWorkers; i++ {
		wg.Add(1)
		go worker(ctx, i, cfg, tasks, &wg)
	}

	// Inicia a descoberta de arquivos
	go func() {
		defer close(tasks)
		if err := discoverFiles(ctx, cfg.RawDir, tasks); err != nil {
			log.Printf("❌ Erro na descoberta de arquivos: %v", err)
		}
	}()

	wg.Wait()
	fmt.Println("✅ Ingestão finalizada ou interrompida.")
}

func worker(ctx context.Context, id int, cfg Config, tasks <-chan Task, wg *sync.WaitGroup) {
	defer wg.Done()
	for {
		select {
		case <-ctx.Done():
			return
		case task, ok := <-tasks:
			if !ok {
				return
			}
			// Cada task tem seu próprio timeout
			taskCtx, taskCancel := context.WithTimeout(ctx, cfg.Timeout)
			if err := processTask(taskCtx, id, cfg.PythonSidecar, task); err != nil {
				log.Printf("[Worker %d] ❌ Erro em %s: %v", id, filepath.Base(task.Path), err)
			}
			taskCancel()
		}
	}
}

func discoverFiles(ctx context.Context, root string, tasks chan<- Task) error {
	return filepath.Walk(root, func(path string, info os.FileInfo, err error) error {
		if err != nil || info.IsDir() {
			return err
		}

		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
		}

		var taskType string
		switch strings.ToLower(filepath.Ext(path)) {
		case ".pdf":
			taskType = "PDF"
		case ".mp3", ".wav", ".m4a":
			taskType = "AUDIO"
		case ".txt", ".md":
			taskType = "NOTE"
		default:
			return nil
		}

		absPath, _ := filepath.Abs(path)
		tasks <- Task{Path: absPath, Type: taskType}
		return nil
	})
}

func processTask(ctx context.Context, workerID int, apiURL string, task Task) error {
	payload, _ := json.Marshal(task)

	for {
		req, err := http.NewRequestWithContext(ctx, "POST", apiURL, bytes.NewBuffer(payload))
		if err != nil {
			return err
		}
		req.Header.Set("Content-Type", "application/json")

		resp, err := http.DefaultClient.Do(req)
		if err != nil {
			return err
		}
		defer resp.Body.Close()

		if resp.StatusCode == http.StatusServiceUnavailable {
			log.Printf("[Worker %d] ⏳ Servidor ocupado. Aguardando 5 segundos para reprocessar %s...", workerID, filepath.Base(task.Path))
			select {
			case <-ctx.Done():
				return ctx.Err()
			case <-time.After(5 * time.Second):
				continue // Tenta novamente
			}
		}

		if resp.StatusCode != http.StatusOK {
			body, _ := io.ReadAll(resp.Body)
			return fmt.Errorf("status %d: %s", resp.StatusCode, string(body))
		}

		fmt.Printf("[Worker %d] ✨ Sucesso: %s\n", workerID, filepath.Base(task.Path))
		return nil
	}
}
