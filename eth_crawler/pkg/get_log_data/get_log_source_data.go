package get_log_data

import (
	"context"
	"fmt"
	"log"
	"math/big"
	"strconv"
	"sync"

	"github.com/ethereum/go-ethereum"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/ethclient"

	CsvWriter "eth_crawler/pkg/csv_writer"
)

func Get_log_source_data_main() {
	wg := &sync.WaitGroup{}
	target_contract := "AAveLiquidation"
	blcokFrom := big.NewInt(12466826)
	blockTo := big.NewInt(14838875)
	blockMax := uint64(14838875)
	blockGap := int64(118602)

	// blcokFrom := big.NewInt(12466826)
	// blockTo := big.NewInt(11838875)
	// blockMax := uint64(14838875)
	// blockGap := int64(300)

	for blcokFrom.Uint64() <= blockMax {
		wg.Add(1)
		blockTo = big.NewInt(blcokFrom.Int64() + blockGap)
		// fmt.Println("start_" + target_contract + "_" + blcokFrom.String() + "_" + blockTo.String())
		go get_log_source_data_loop(target_contract, blcokFrom, blockTo, wg)
		blcokFrom = blockTo
	}
	wg.Wait()

}

func get_log_source_data_loop(target_contract string, blcokFrom *big.Int, blockTo *big.Int, wg *sync.WaitGroup) {
	defer wg.Done()

	fmt.Println("start_source_" + target_contract + "_" + blcokFrom.String() + "_" + blockTo.String())
	// config
	archive_node := "http://localhost:19545"
	// api_key := "JSPD2IG21CPF9PHIKQP4IEW9R8KN1NJSYH"
	// abi_file_location := "./data/abi/"
	save_file_path := "data/crawled/"
	// contract_name_file_path := "./data/export-verified-contractaddress-opensource-license.csv"

	// https://api.etherscan.io/api?module=logs&action=getLogs&fromBlock=379224&toBlock=latest&address=0x33990122638b9132ca29c723bdf037f1a891a70c&topic0=0xf63780e752c6a54a94fc52715dbc5518a3b4c3c2833d301a204226548a2a8545&apikey=JSPD2IG21CPF9PHIKQP4IEW9R8KN1NJSYH

	var contract_address string
	var log_csv string
	var log_headers []string
	var topic0_target string

	// blcokFrom := big.NewInt(12466826)
	// // blockTo := big.NewInt(12466826 + 100)
	// blockTo := big.NewInt(13000000)
	// blockTo := big.NewInt(13500000)
	// blockTo := big.NewInt(14000000)
	// blockTo := big.NewInt(14500000)
	// blockTo := big.NewInt(14838875)

	// blcokFrom := big.NewInt(13000000)
	// blockTo := big.NewInt(13500000)

	// blcokFrom := big.NewInt(13500000)
	// blockTo := big.NewInt(14000000)

	// blcokFrom := big.NewInt(14000000)
	// blockTo := big.NewInt(14500000)

	if target_contract == "ChainLink" {
		contract_address = "0x37bC7498f4FF12C19678ee8fE19d713b87F6a9e6"
		log_csv = "chainlink_eth_usd_gas_info_" + blcokFrom.String() + "_" + blockTo.String() + ".csv"
		log_headers = []string{
			"blockNum", "index", "txHash", "gas", "gasPrice", "gasTipCap", "gasFeeCap",
		}
		topic0_target = "0x0559884fd3a460db3073b7fc896cc77986f16e378210ded43186175bf646fc5f"
	}

	if target_contract == "MakerDAO_ETH_USD_Median" {
		contract_address = "0x64DE91F5A373Cd4c28de3600cB34C7C6cE410C85"
		log_csv = "maker_dao_eth_usd_median_gas_info_" + blcokFrom.String() + "_" + blockTo.String() + ".csv"
		log_headers = []string{
			"blockNum", "index", "txHash", "gas", "gasPrice", "gasTipCap", "gasFeeCap",
		}
		topic0_target = "0xb78ebc573f1f889ca9e1e0fb62c843c836f3d3a2e1f43ef62940e9b894f4ea4c"
	}

	if target_contract == "AAveLiquidation" {
		contract_address = "0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9"
		log_csv = "aave_liquidationcall_gas_info_" + blcokFrom.String() + "_" + blockTo.String() + ".csv"
		log_headers = []string{
			"blockNum", "index", "txHash", "gas", "gasPrice", "gasTipCap", "gasFeeCap",
		}
		topic0_target = "0xe413a321e8681d831f4dbccbca790d2952b56f977908e45be37335533e005286"
	}

	// Create a client instance to connect to our providr
	client, err := ethclient.Dial(archive_node)
	if err != nil {
		fmt.Println(err)
	}

	contractAddress := common.HexToAddress(contract_address)
	query := ethereum.FilterQuery{
		FromBlock: blcokFrom,
		ToBlock:   blockTo, //(12466826 + 100), //14838875),
		Addresses: []common.Address{
			contractAddress,
		},
	}
	logs, err := client.FilterLogs(context.Background(), query)
	if err != nil {
		log.Fatal(err)
	}

	// abi_string := GetContractInfo.GetAbi(api_key, contract_address, contract_address, abi_file_location)
	// contractAbi, err := abi.JSON(strings.NewReader(abi_string))
	if err != nil {
		log.Fatal(err)
	}

	log_file, log_writer, _ := CsvWriter.Get_writer(save_file_path, log_csv, log_headers)
	defer log_file.Close()
	defer log_writer.Flush()

	for _, vLog := range logs {
		// fmt.Println("*********************************")
		// fmt.Println(vLog.BlockHash.Hex()) // 0x3404b8c050aa0aacd0223e91b5c32fee6400f357764771d0684fa7b3f448f1a8
		// fmt.Println(vLog.BlockNumber)     // 2394201
		// fmt.Println(vLog.TxHash.Hex())    // 0xfa10370d60c86502d8e2da878a75cf0a754926887a7d861832da204e76066186
		// fmt.Println(vLog.Index)           // 0xfa10370d60c86502d8e2da878a75cf0a754926887a7d861832da204e76066186

		// event := struct {
		// 	Key   [32]byte
		// 	Value [32]byte
		// }{}
		// _, err := contractAbi.Unpack("AnswerUpdated", vLog.Data)
		// if err != nil {
		// 	log.Fatal(err)
		// }
		// fmt.Println("------------------------")
		// fmt.Println(event) // foo
		// fmt.Println("------------------------")
		// fmt.Println(string(event.Value[:])) // bar

		if vLog.Topics[0].Hex() == topic0_target {
			tx, _, err := client.TransactionByHash(context.Background(), vLog.TxHash)

			if err != nil {
				log.Fatal(err)
			}

			len_heder := uint(len(log_headers))
			topics := make([]string, len_heder)
			// "blockNum", "index", "txHash" ,"gas", "gasPrice", "gasTipCap", "gasFeeCap",

			topics[0] = strconv.FormatUint(uint64(vLog.BlockNumber), 10)
			topics[1] = strconv.FormatUint(uint64(vLog.Index), 10)
			topics[2] = vLog.TxHash.Hex()
			topics[3] = strconv.FormatUint(tx.Gas(), 10)
			topics[4] = tx.GasPrice().String()
			topics[5] = tx.GasTipCap().String()
			topics[6] = tx.GasFeeCap().String()

			log_writer.Write(topics[:])
		}

		// fmt.Println(topics[0]) // 0xe79e73da417710ae99aa2088575580a60415d359acfad9cdd3382d59c80281d4
	}

	// eventSignature := []byte("ItemSet(bytes32,bytes32)")
	// hash := crypto.Keccak256Hash(eventSignature)
	// fmt.Println(hash.Hex()) // 0xe79e73da417710ae99aa2088575580a60415d359acfad9cdd3382d59c80281d4
}
