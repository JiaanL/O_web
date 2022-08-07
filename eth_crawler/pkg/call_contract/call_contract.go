package call_contract

import (
	"context"
	"encoding/hex"
	"fmt"
	"log"
	"math/big"
	"sync"

	"github.com/ethereum/go-ethereum"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/ethclient"
)

func CallContract() {
	archive_node := "http://localhost:19545"
	// api_key := "JSPD2IG21CPF9PHIKQP4IEW9R8KN1NJSYH"
	// abi_file_location := "./data/abi/"
	// save_file_path := "data/crawled/"
	// contract_name_file_path := "./data/export-verified-contractaddress-opensource-license.csv"

	// https://api.etherscan.io/api?module=logs&action=getLogs&fromBlock=379224&toBlock=latest&address=0x33990122638b9132ca29c723bdf037f1a891a70c&topic0=0xf63780e752c6a54a94fc52715dbc5518a3b4c3c2833d301a204226548a2a8545&apikey=JSPD2IG21CPF9PHIKQP4IEW9R8KN1NJSYH

	// Create a client instance to connect to our providr
	client, err := ethclient.Dial(archive_node)
	if err != nil {
		fmt.Println(err)
	}
	// var msg ethereum.CallMsg
	// var blockNum *big.Int
	to_contract := common.HexToAddress("0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419")
	decoded_data, _ := hex.DecodeString("245a7bfc")
	msg := ethereum.CallMsg{
		To:   &to_contract, // the destination contract (nil for contract creation)
		Data: decoded_data, // input data, usually an ABI-encoded contract method invocation
	}
	wg := &sync.WaitGroup{}
	for blockNum_int := 10506501; blockNum_int < 14971330; {
		wg.Add(1)
		go search_loop(client, msg, blockNum_int, blockNum_int+100000, wg)
		blockNum_int = blockNum_int + 100000
	}
	wg.Wait()

	// search_loop(client, msg)
	// var result_data string
	// for blockNum_int := 10606501; blockNum_int < 14971330; blockNum_int++ {
	// 	blockNum = big.NewInt(int64(blockNum_int))
	// 	// blockNum = big.NewInt(10999698)
	// 	result, err := client.CallContract(context.Background(), msg, blockNum)

	// 	if err != nil {
	// 		log.Fatal(err)
	// 	}

	// 	result_data_tmp := hex.EncodeToString(result)

	// 	if result_data_tmp != result_data {
	// 		result_data = result_data_tmp
	// 		println(result_data)
	// 		println(blockNum_int)
	// 		println("-----------------------------------")
	// 	}

	// }

}

func search_loop(client *ethclient.Client, msg ethereum.CallMsg, from int, to int, wg *sync.WaitGroup) {
	defer wg.Done()
	var result_data string
	for blockNum_int := from; blockNum_int <= to; blockNum_int++ {
		blockNum := big.NewInt(int64(blockNum_int))
		// blockNum = big.NewInt(10999698)
		result, err := client.CallContract(context.Background(), msg, blockNum)

		if err != nil {
			log.Fatal(err)
		}

		result_data_tmp := hex.EncodeToString(result)
		if result_data == "" {
			result_data = result_data_tmp
		}
		if result_data_tmp != result_data {
			result_data = result_data_tmp
			println(result_data)
			println(blockNum_int)
			println("-----------------------------------")
		}

	}
}
