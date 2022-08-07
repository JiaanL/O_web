package get_block_data

import (
	"context"
	"log"
	"math/big"
	"sync"

	"github.com/ethereum/go-ethereum/ethclient"

	CsvWriter "eth_crawler/pkg/csv_writer"
)

func Get_gas_fee_main() {
	save_file_path := "data/crawled/"

	file_num := "1_1"
	log_csv := "blockBaseFee_data_" + file_num + ".csv"
	log_headers := []string{
		"blockNum", "baseFee",
	}
	wg := &sync.WaitGroup{}
	log_file, log_writer, _ := CsvWriter.Get_writer(save_file_path, log_csv, log_headers)
	defer log_file.Close()
	defer log_writer.Flush()

	blockTo := big.NewInt(14838875)
	var blcokFrom *big.Int
	var blockMax uint64

	// blockMax := uint64(14838875)
	blockGap := int64(10000)

	// 1 ---------------------------

	if file_num == "0" {
		blcokFrom = big.NewInt(12466826)
		blockMax = uint64(12800000)
	}

	if file_num == "1_1" {
		blcokFrom = big.NewInt(12800000)
		blockMax = uint64(13000000)
	}

	// 2 ---------------------------
	if file_num == "2" {
		blcokFrom = big.NewInt(13000000)
		blockMax = uint64(13400000)
	}

	// 3 ---------------------------
	if file_num == "3" {
		blcokFrom = big.NewInt(13400000)
		blockMax = uint64(13800000)
	}

	// 4 ---------------------------
	if file_num == "4" {
		blcokFrom = big.NewInt(13800000)
		blockMax = uint64(14200000)
	}

	// 5 ---------------------------
	if file_num == "5" {
		blcokFrom = big.NewInt(14200000)
		blockMax = uint64(14600000)
	}

	// 6 ---------------------------
	if file_num == "6" {
		blcokFrom = big.NewInt(14600000)
		blockMax = uint64(14838875)
	}

	c := make(chan [][2]string, 45)
	counter := 0

	for blcokFrom.Uint64() <= blockMax {

		wg.Add(1)
		blockTo = big.NewInt(blcokFrom.Int64() + blockGap)
		// fmt.Println("start_" + target_contract + "_" + blcokFrom.String() + "_" + blockTo.String())
		go get_gas_fee_loop(blcokFrom, blockTo, wg, c)
		blcokFrom = blockTo

		counter++
	}
	wg.Wait()

	var final_result [][2]string

	for i := 0; i < counter; i++ {
		final_result = append(final_result, <-c...)
	}

	for _, v := range final_result {
		log_writer.Write(v[:])
	}

}

func get_gas_fee_loop(blockFrom *big.Int, blockTo *big.Int, wg *sync.WaitGroup, c chan [][2]string) {

	defer wg.Done()

	client, err := ethclient.Dial("http://localhost:19545")
	if err != nil {
		log.Fatal(err)
	}

	blockNumber := blockFrom.Uint64()
	// blockGap := 118602
	blockMax := blockTo.Uint64()

	var block_data_array [][2]string

	for blockNumber <= blockMax {
		blockNumber = blockNumber + 1
		header, err := client.HeaderByNumber(context.Background(), big.NewInt(int64(blockNumber)))
		if err != nil {
			log.Fatal(err)
		}

		var block_data [2]string
		block_data[0] = header.Number.String()
		block_data[1] = header.BaseFee.String()

		block_data_array = append(block_data_array, block_data)
		// log_writer.Write(block_data[:])

	}
	c <- block_data_array
}
