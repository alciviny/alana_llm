package main

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"strings"
)

// InputChunker representa o texto bruto e os parâmetros de divisão
type InputChunker struct {
	Text         string `json:"text"`
	MaxTokens    int    `json:"max_tokens"` // Estimado por caracteres p/ simplicidade
	OverlapChars int    `json:"overlap_chars"`
}

// ChunkResult representa um pedaço do texto processado
type ChunkResult struct {
	Index   int    `json:"index"`
	Content string `json:"content"`
}

func main() {
	// Lê a entrada do Python
	rawInput, err := io.ReadAll(os.Stdin)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Erro na leitura: %v\n", err)
		os.Exit(1)
	}

	var input InputChunker
	if err := json.Unmarshal(rawInput, &input); err != nil {
		fmt.Fprintf(os.Stderr, "Erro no JSON: %v\n", err)
		os.Exit(1)
	}

	// Algoritmo de Chunking Paralelo
	// Dividimos o texto em "Sentenças" (ponto final) para não quebrar no meio de frases
	sentences := strings.Split(input.Text, ". ")
	
	var chunks []ChunkResult
	currentChunk := ""
	chunkIdx := 0
	
	// Nota: Para ser 100% paralelo em documentos gigantes, poderíamos dividir o texto 
	// em blocos maiores e processar cada um. Aqui faremos uma divisão linear ultra-rápida.
	for _, sentence := range sentences {
		if len(currentChunk)+len(sentence) > input.MaxTokens {
			chunks = append(chunks, ChunkResult{
				Index:   chunkIdx,
				Content: strings.TrimSpace(currentChunk),
			})
			
			// Mantém o overlap para contexto
			overlapStart := len(currentChunk) - input.OverlapChars
			if overlapStart < 0 { overlapStart = 0 }
			currentChunk = currentChunk[overlapStart:] + " " + sentence + ". "
			chunkIdx++
		} else {
			currentChunk += sentence + ". "
		}
	}

	if currentChunk != "" {
		chunks = append(chunks, ChunkResult{
			Index:   chunkIdx,
			Content: strings.TrimSpace(currentChunk),
		})
	}

	// Devolve o resultado em JSON
	output, _ := json.Marshal(chunks)
	fmt.Print(string(output))
}
