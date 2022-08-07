// reference : https://github.com/sinakhalili/abigenz

package get_contract_info

import (
	"encoding/csv"
	"encoding/json"
	"fmt"
	"io"
	"io/ioutil"
	"log"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"strings"
)

type EtherscanResponse struct {
	Status  string `json:"status"`
	Message string `json:"message"`
	Result  string `json:"result"`
}

func GetNameBook(contract_name_file_path string) map[string]string {
	// open file
	f, err := os.Open(contract_name_file_path)
	if err != nil {
		log.Fatal(err)
	}

	// remember to close the file at the end of the program
	defer f.Close()

	// read csv values using csv.Reader
	csvReader := csv.NewReader(f)
	data, err := csvReader.ReadAll()
	if err != nil {
		log.Fatal(err)
	}

	m := make(map[string]string)

	for i, line := range data {
		if i > 0 {
			address := line[1]
			name := line[2]
			m[address] = name
		}

	}
	return m

}

func GetAbiFromLocal(contract_name string, abi_location string) (abi_result string) {
	var files []string

	root := abi_location
	err := filepath.Walk(root, func(path string, info os.FileInfo, err error) error {
		files = append(files, path)
		return nil
	})
	if err != nil {
		panic(err)
	}
	for _, file := range files {
		tmp_file_name_array := strings.Split(file, "/")
		tmp_file_name := tmp_file_name_array[len(tmp_file_name_array)-1]
		if tmp_file_name == contract_name+".json" {
			log.Printf("ABI already saved")
			jsonFile, err := os.Open(file)
			if err != nil {
				fmt.Println(err)
			}
			defer jsonFile.Close()
			byteValue, _ := ioutil.ReadAll(jsonFile)
			abi_result = string(byteValue)
			return
		}
	}
	return
}

func GetAbiFromOnline(etherscan_api_key string, contract_address string, contract_name string, abi_location string) (abi_result string) {
	if etherscan_api_key == "" {
		log.Printf("Error: No API key")
		return
	}

	base, err := url.Parse("https://api.etherscan.io/api")
	if err != nil {
		return
	}

	params := url.Values{}
	params.Add("module", "contract")
	params.Add("action", "getabi")
	params.Add("address", contract_address)
	params.Add("apiKey", etherscan_api_key)
	base.RawQuery = params.Encode()

	resp, err := http.Get(base.String())
	if err != nil {
		log.Println("Oh no! Got: ")

		body, err := io.ReadAll(resp.Body)
		log.Println(string(body))
		log.Fatalln(err)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		log.Fatalln(err)
	}

	var etherscan_response EtherscanResponse
	err = json.Unmarshal(body, &etherscan_response)
	if err != nil {
		log.Fatal(err)
	}

	log.Printf("Etherscan says: %s\n", etherscan_response.Message)
	if etherscan_response.Message == "NOTOK" {
		log.Fatal("Error: ", etherscan_response.Result)
	}

	// tokenName := contract_name
	abi_result_byte := []byte(etherscan_response.Result)
	filename := abi_location + contract_name + ".json"
	if err := os.WriteFile(filename, abi_result_byte, 0666); err != nil {
		log.Fatal(err)
	}
	log.Println("Abi in ", filename)

	abi_result = string(abi_result_byte)

	return
}

func GetAbi(etherscan_api_key string, contract_address string, contract_name string, abi_location string) (abi_result string) {

	abi_result = GetAbiFromLocal(contract_name, abi_location)

	if abi_result == "" {
		abi_result = GetAbiFromOnline(etherscan_api_key, contract_address, contract_name, abi_location)
	}

	return
}
