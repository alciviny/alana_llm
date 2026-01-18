package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"sync"
	"syscall"
)

// Task define a estrutura de uma tarefa de processamento.
type Task struct {
	Path string `json:"path"`
	Type string `json:"type"`
}

const (
	rawDir        = "./data/raw"
	numWorkers    = 4 // Número de goroutines concorrentes
	pythonSidecar = "http://127.0.0.1:8000/process_document"
)

func main() {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// Captura Ctrl+C para cancelamento gracioso
	sig := make(chan os.Signal, 1)
	signal.Notify(sig, os.Interrupt, syscall.SIGTERM)
	go func() {
		<-sig
		fmt.Println("\n⛔ Cancelando ingestão...")
		cancel()
	}()

	tasks := make(chan Task, 100)
	var wg sync.WaitGroup

	// Inicia os workers
	for i := 1; i <= numWorkers; i++ {
		wg.Add(1)
		go worker(ctx, i, tasks, &wg)
	}

	// Inicia a descoberta de arquivos em uma goroutine separada
	go func() {
		defer close(tasks) // Fecha o canal de tarefas quando a descoberta terminar
		if err := discoverFiles(ctx, rawDir, tasks); err != nil {
			fmt.Println("Erro na descoberta de arquivos:", err)
		}
	}()

	wg.Wait()
	fmt.Println("✅ Ingestão concluída pelo Orquestrador Go")
}

func worker(ctx context.Context, id int, tasks <-chan Task, wg *sync.WaitGroup) {
	defer wg.Done()
	for {
		select {
		case <-ctx.Done():
			fmt.Printf("[Worker %d] Cancelado.\n", id)
			return
		case task, ok := <-tasks:
			if !ok {
				return // Canal fechado
			}
			if err := processTask(ctx, id, task); err != nil {
				fmt.Printf("[Worker %d] Erro ao processar task para %s: %v\n", id, task.Path, err)
			}
		}
	}
}

func discoverFiles(ctx context.Context, root string, tasks chan<- Task) error {
	return filepath.Walk(root, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if info.IsDir() {
			return nil
		}

		// Verifica o contexto para cancelamento
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
		}

		// Determina o tipo e envia a tarefa
		var taskType string
		switch filepath.Ext(path) {
		case ".pdf":
			taskType = "PDF"
		case ".mp3", ".wav", ".m4a":
			taskType = "Audio"
		case ".txt", ".md":
			taskType = "Note"
		default:
			return nil // Ignora arquivos não suportados
		}
		
		// Converte para caminho absoluto para garantir que o Python encontre
		absPath, err := filepath.Abs(path)
		if err != nil {
			fmt.Printf("Não foi possível obter caminho absoluto para %s: %v\n", path, err)
			return nil // Pula este arquivo
		}
		
		tasks <- Task{Path: absPath, Type: taskType}
		return nil
	})
}

// processTask agora faz uma chamada HTTP para o sidecar Python
func processTask(ctx context.Context, workerID int, task Task) error {
	fmt.Printf("[Worker %d] Enviando para API: %s (%s)\n", workerID, task.Type, task.Path)

	payload, err := json.Marshal(task)
	if err != nil {
		return fmt.Errorf("erro ao converter payload para JSON: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, "POST", pythonSidecar, bytes.NewBuffer(payload))
	if err != nil {
		return fmt.Errorf("erro ao criar requisição HTTP: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return fmt.Errorf("erro na chamada HTTP para o sidecar: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := ioutil.ReadAll(resp.Body)
		return fmt.Errorf("API retornou status não-OK: %s. Body: %s", resp.Status, string(body))
	}

	fmt.Printf("[Worker %d] Sucesso para: %s\n", workerID, task.Path)
	return nil
}
