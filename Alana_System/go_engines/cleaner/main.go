package main

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"regexp"
	"strings"
	"sync"
)

type InputData struct {
	Pages map[string]string `json:"pages"`
}

type CleanedPage struct {
	PageNumber string `json:"page_number"`
	Text       string `json:"text"`
	CharCount  int    `json:"char_count"`
}

type TurboCleaner struct {
	whitespaceRegex *regexp.Regexp
	hyphenRegex     *regexp.Regexp
	lineBreaksRegex *regexp.Regexp
}

func NewTurboCleaner() *TurboCleaner {
	return &TurboCleaner{
		whitespaceRegex: regexp.MustCompile(`[ \t]+`),
		// (.) garante que pegamos qualquer caractere (inclusive acentuados) após a quebra
		hyphenRegex:     regexp.MustCompile(`-\r?\n(.)`), 
		lineBreaksRegex: regexp.MustCompile(`\n{3,}`),
	}
}

func (c *TurboCleaner) CleanPage(pageNum string, rawText string) CleanedPage {
	// 1. Une hifenização
	text := c.hyphenRegex.ReplaceAllString(rawText, "$1")
	
	// 2. Normaliza espaços
	text = c.whitespaceRegex.ReplaceAllString(text, " ")
	
	// 3. Normaliza quebras
	text = c.lineBreaksRegex.ReplaceAllString(text, "\n\n")
	
	return CleanedPage{
		PageNumber: pageNum,
		Text:       strings.TrimSpace(text),
		CharCount:  len(text),
	}
}

func main() {
	rawInput, err := io.ReadAll(os.Stdin)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Erro ao ler entrada: %v\n", err)
		os.Exit(1)
	}

	var input InputData
	if err := json.Unmarshal(rawInput, &input); err != nil {
		fmt.Fprintf(os.Stderr, "Erro ao decodificar JSON: %v\n", err)
		os.Exit(1)
	}

	cleaner := NewTurboCleaner()
	var wg sync.WaitGroup
	results := make([]CleanedPage, len(input.Pages))
	
	var mu sync.Mutex
	i := 0
	for num, text := range input.Pages {
		wg.Add(1)
		go func(pNum string, pText string, idx int) {
			defer wg.Done()
			cleaned := cleaner.CleanPage(pNum, pText)
			mu.Lock()
			results[idx] = cleaned
			mu.Unlock()
		}(num, text, i)
		i++
	}
	
	wg.Wait()

	output, _ := json.Marshal(results)
	fmt.Print(string(output))
}
