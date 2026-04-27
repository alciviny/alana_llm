package main

import (
	"reflect"
	"testing"
)

func TestFindPath(t *testing.T) {
	edges := []Edge{
		{From: "A", To: "B"},
		{From: "B", To: "C"},
		{From: "C", To: "D"},
		{From: "A", To: "X"},
		{From: "X", To: "D"},
	}
	engine := NewGraphEngine(edges)

	// Teste de caminho mais curto (BFS deve preferir A-X-D sobre A-B-C-D)
	expected := []string{"A", "X", "D"}
	result := engine.FindPath("A", "D")

	if !reflect.DeepEqual(result, expected) {
		t.Errorf("Caminho incorreto. Esperado %v, obtido %v", expected, result)
	}
}

func TestNeighbors(t *testing.T) {
	edges := []Edge{
		{From: "A", To: "B"},
		{From: "A", To: "C"},
	}
	engine := NewGraphEngine(edges)

	expected := []string{"B", "C"}
	result := engine.Adjacency["A"]

	if !reflect.DeepEqual(result, expected) {
		t.Errorf("Vizinhos incorretos. Esperado %v, obtido %v", expected, result)
	}
}
