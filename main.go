package main

import (
	"bufio"
	"crypto/tls"
	"fmt"
	"log"
	"os"
	"strings"
	"sync"
)

func checkHost(host string) error {
	_, err := tls.Dial("tcp", host, nil)

	return err
}

func writeFile(file *os.File, url <-chan string, wg *sync.WaitGroup) {
	for u := range url {
		file.WriteString(u + "\n")
	}

	wg.Done()
}

func worker(url <-chan string, valid chan<- string, unvalid chan<- string,
	wg *sync.WaitGroup) {

	for hostname := range url {
		err := checkHost(hostname + ":443")
		if err != nil {
			unvalid <- hostname
		} else {
			valid <- hostname
		}
	}

	wg.Done()
}

func readFile(file *os.File, url chan<- string) {
	reader := bufio.NewScanner(file)
	for reader.Scan() {
		h_s := strings.Split(reader.Text(), "://")
		url <- h_s[len(h_s)-1]
	}
}

func main() {
	urlChan := make(chan string)
	validChan := make(chan string)
	unvalidChan := make(chan string)

	wgWork := sync.WaitGroup{}
	wgWrite := sync.WaitGroup{}

	for i := 0; i < 1; i++ {
		go worker(urlChan, validChan, unvalidChan, &wgWork)
		wgWork.Add(1)
	}

	fileValid, err := os.Create("valid")
	if err != nil {
		log.Fatal(err)
	}
	defer fileValid.Close()

	fileUnvalid, err := os.Create("unvalid")
	if err != nil {
		log.Fatal(err)
	}
	defer fileUnvalid.Close()

	go writeFile(fileValid, validChan, &wgWrite)
	wgWrite.Add(1)
	go writeFile(fileUnvalid, unvalidChan, &wgWrite)
	wgWrite.Add(1)

	fileInput, err := os.Open("urls")
	if err != nil {
		log.Fatal(err)
	}
	defer fileInput.Close()

	readFile(fileInput, urlChan)

	close(urlChan)
	wgWork.Wait()

	close(validChan)
	close(unvalidChan)
	wgWrite.Wait()

	fmt.Printf("Done.\n")
}
