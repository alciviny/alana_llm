package main

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"sync"
)

// Edge representa uma conexão no grafo
type Edge struct {
	From string `json:"from"`
	To   string `json:"to"`
	Type string `json:"type"`
}

// GraphInput representa os dados enviados pelo Python
type GraphInput struct {
	Edges  []Edge `json:"edges"`
	Source string `json:"source"`
	Target string `json:"target"`
	Mode   string `json:"mode"` // "path", "neighbors", "density"
}

// GraphEngine gerencia a estrutura de adjacência
type GraphEngine struct {
	Adjacency map[string][]string
	mu        sync.RWMutex
}

func NewGraphEngine(edges []Edge) *GraphEngine {
	engine := &GraphEngine{
		Adjacency: make(map[string][]string),
	}
	for _, edge := range edges {
		engine.Adjacency[edge.From] = append(engine.Adjacency[edge.From], edge.To)
		// Se for não-direcionado, descomente:
		// engine.Adjacency[edge.To] = append(engine.Adjacency[edge.To], edge.From)
	}
	return engine
}

// FindPath busca o caminho mais curto entre dois nós (BFS)
func (g *GraphEngine) FindPath(start, end string) []string {
	if start == end {
		return []string{start}
	}

	queue := [][]string{{start}}
	visited := map[string]bool{start: true}

	for len(queue) > 0 {
		path := queue[0]
		queue = queue[1:]
		node := path[len(path)-1]

		for _, neighbor := range g.Adjacency[node] {
			if neighbor == end {
				return append(path, end)
			}
			if !visited[neighbor] {
				visited[neighbor] = true
				newPath := append([]string{}, path...)
				newPath = append(newPath, neighbor)
				queue = append(queue, newPath)
			}
		}
	}
	return nil
}

func main() {
	rawInput, _ := io.ReadAll(os.Stdin)
	var input GraphInput
	json.Unmarshal(rawInput, &input)

	engine := NewGraphEngine(input.Edges)
	
	var result interface{}

	switch input.Mode {
	case "path":
		result = engine.FindPath(input.Source, input.Target)
	case "neighbors":
		result = engine.Adjacency[input.Source]
	case "density":
		result = len(input.Edges)
	}

	output, _ := json.Marshal(result)
	fmt.Print(string(output))
}
