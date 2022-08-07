package get_log_data

import (
	"context"
	"encoding/hex"
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

func Get_log_data_main() {
	wg := &sync.WaitGroup{}
	target_contract := "ChainLink_USDC_ETH"

	// blcokFrom := big.NewInt(12382429)

	// Latest analysis range
	blcokFrom := big.NewInt(12466826)
	blockTo := big.NewInt(14838875)
	blockMax := uint64(14838875)
	blockGap := int64(118602)

	// Chainlink Previous data
	if target_contract == "ChainLinkOnChainAGG" {
		blcokFrom = big.NewInt(11008985)
		blockTo = big.NewInt(12187956)
		blockMax = uint64(12187956)
		blockGap = int64(100000)
	}

	if target_contract == "ChainLink" {
		blcokFrom = big.NewInt(12187956)
		blockTo = big.NewInt(14838875)
		blockMax = uint64(14838875)
		blockGap = int64(100000)
	}

	if target_contract == "UniswapV2_USDC_ETH" {
		blcokFrom = big.NewInt(11008985)
		blockTo = big.NewInt(14838875)
		blockMax = uint64(14838875)
		blockGap = int64(50000)
	}

	if target_contract == "MakerDAO_ETH_USD_Median" {
		blcokFrom = big.NewInt(11008985)
		blockTo = big.NewInt(14838875)
		blockMax = uint64(14838875)
		blockGap = int64(50000)
	}

	// blcokFrom := big.NewInt(12466826)
	// blockTo := big.NewInt(11838875)
	// blockMax := uint64(14838875)
	// blockGap := int64(300)

	for blcokFrom.Uint64() <= blockMax {
		wg.Add(1)
		blockTo = big.NewInt(blcokFrom.Int64() + blockGap)
		// fmt.Println("start_" + target_contract + "_" + blcokFrom.String() + "_" + blockTo.String())
		// get_log_data_loop(target_contract, blcokFrom, blockTo, wg)
		get_log_data_loop(target_contract, blcokFrom, blockTo, wg)
		blcokFrom = blockTo
	}
	wg.Wait()

}

func get_log_data_loop(target_contract string, blcokFrom *big.Int, blockTo *big.Int, wg *sync.WaitGroup) {
	defer wg.Done()

	fmt.Println("start_" + target_contract + "_" + blcokFrom.String() + "_" + blockTo.String())
	// config
	archive_node := "http://localhost:19545"
	// api_key := "JSPD2IG21CPF9PHIKQP4IEW9R8KN1NJSYH"
	// abi_file_location := "./data/abi/"
	var save_file_path string
	save_file_path = "data/crawled/"
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
		if blcokFrom.Int64() < 12453812 {
			contract_address = "0xd3fcd40153e56110e6eeae13e12530e26c9cb4fd"
		}
		save_file_path = "data/crawled/chainlink/"
		log_csv = "chainlink_eth_usd_" + blcokFrom.String() + "_" + blockTo.String() + ".csv"
		log_headers = []string{
			"topic0", "current", "roundId", "updatedAt", "blockNum", "index",
		}
		topic0_target = "0x0559884fd3a460db3073b7fc896cc77986f16e378210ded43186175bf646fc5f"
	}

	if target_contract == "ChainLink_DAI_ETH" {
		contract_address = "0x158228e08C52F3e2211Ccbc8ec275FA93f6033FC"
		save_file_path = "data/crawled/chainlink/"
		log_csv = "chainlink_dai_eth_" + blcokFrom.String() + "_" + blockTo.String() + ".csv"
		log_headers = []string{
			"topic0", "current", "roundId", "updatedAt", "blockNum", "index",
		}
		topic0_target = "0x0559884fd3a460db3073b7fc896cc77986f16e378210ded43186175bf646fc5f"
	}

	if target_contract == "ChainLink_USDT_ETH" {
		contract_address = "0x7de0d6fce0c128395c488cb4df667cdbfb35d7de"
		save_file_path = "data/crawled/chainlink/"
		log_csv = "chainlink_usdt_eth_" + blcokFrom.String() + "_" + blockTo.String() + ".csv"
		log_headers = []string{
			"topic0", "current", "roundId", "updatedAt", "blockNum", "index",
		}
		topic0_target = "0x0559884fd3a460db3073b7fc896cc77986f16e378210ded43186175bf646fc5f"
	}

	if target_contract == "ChainLink_USDC_ETH" {
		contract_address = "0xe5BbBdb2Bb953371841318E1Edfbf727447CeF2E"
		save_file_path = "data/crawled/chainlink/"
		log_csv = "chainlink_usdc_eth_" + blcokFrom.String() + "_" + blockTo.String() + ".csv"
		log_headers = []string{
			"topic0", "current", "roundId", "updatedAt", "blockNum", "index",
		}
		topic0_target = "0x0559884fd3a460db3073b7fc896cc77986f16e378210ded43186175bf646fc5f"
	}

	if target_contract == "ChainLinkOnChainAGG" {
		contract_address = "0x00c7A37B03690fb9f41b5C5AF8131735C7275446"
		save_file_path = "data/crawled/chainlink/"
		log_csv = "chainlink_on_chain_eth_usd_" + blcokFrom.String() + "_" + blockTo.String() + ".csv"
		log_headers = []string{
			"topic0", "current", "roundId", "updatedAt", "blockNum", "index",
		}
		topic0_target = "0x0559884fd3a460db3073b7fc896cc77986f16e378210ded43186175bf646fc5f"
	}

	if target_contract == "UniswapV2_USDT_ETH" {
		contract_address = "0x0d4a11d5eeaac28ec3f61d100daf4d40471f1852"
		log_csv = "uniswap_v2_eth_usdt_" + blcokFrom.String() + "_" + blockTo.String() + ".csv"
		log_headers = []string{
			"topic0", "reserve0", "reserve1", "blockNum", "index",
		}
		topic0_target = "0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1"
	}

	if target_contract == "UniswapV2_USDC_ETH" {
		contract_address = "0xb4e16d0168e52d35cacd2c6185b44281ec28c9dc"
		save_file_path = "data/crawled/uniswap/"
		log_csv = "uniswap_v2_eth_usdc_" + blcokFrom.String() + "_" + blockTo.String() + ".csv"
		log_headers = []string{
			"topic0", "reserve0", "reserve1", "blockNum", "index",
		}
		topic0_target = "0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1"
	}

	if target_contract == "UniswapV3_USDC_ETH_03" {
		contract_address = "0x8ad599c3A0ff1De082011EFDDc58f1908eb6e6D8"
		log_csv = "uniswap_v3_eth_usdc_03_" + blcokFrom.String() + "_" + blockTo.String() + ".csv"
		log_headers = []string{
			"topic0", "topic1", "topic2", "Data", "blockNum", "index",
		}
		topic0_target = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"
	}

	if target_contract == "UniswapV3_USDC_ETH_005" {
		contract_address = "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640"
		save_file_path = "data/crawled/uniswap/"
		log_csv = "uniswap_v3_eth_usdc_005_" + blcokFrom.String() + "_" + blockTo.String() + ".csv"
		log_headers = []string{
			"topic0", "topic1", "topic2", "Data", "blockNum", "index",
		}
		topic0_target = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"
	}

	if target_contract == "UniswapV3_USDT_ETH_03" {
		contract_address = "0x4e68Ccd3E89f51C3074ca5072bbAC773960dFa36"
		log_csv = "uniswap_v3_eth_usdt_03_" + blcokFrom.String() + "_" + blockTo.String() + ".csv"
		log_headers = []string{
			"topic0", "topic1", "topic2", "Data", "blockNum", "index",
		}
		topic0_target = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"
	}

	if target_contract == "UniswapV3_USDT_ETH_005" {
		contract_address = "0x11b815efB8f581194ae79006d24E0d814B7697F6"
		log_csv = "uniswap_v3_eth_usdt_005_" + blcokFrom.String() + "_" + blockTo.String() + ".csv"
		log_headers = []string{
			"topic0", "topic1", "topic2", "Data", "blockNum", "index",
		}
		topic0_target = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"
	}

	if target_contract == "MakerDAO_ETH_USD_Median" {
		contract_address = "0x64DE91F5A373Cd4c28de3600cB34C7C6cE410C85"
		save_file_path = "data/crawled/makerdao/"
		log_csv = "maker_dao_eth_usd_median_" + blcokFrom.String() + "_" + blockTo.String() + ".csv"
		log_headers = []string{
			"topic0", "Data", "blockNum", "index",
		}
		topic0_target = "0xb78ebc573f1f889ca9e1e0fb62c843c836f3d3a2e1f43ef62940e9b894f4ea4c"
	}

	if target_contract == "MakerDAO_ETH_USD_OSM" {
		contract_address = "0x81FE72B5A8d1A857d176C3E7d5Bd2679A9B85763"
		log_csv = "maker_dao_eth_usd_osm_" + blcokFrom.String() + "_" + blockTo.String() + ".csv"
		log_headers = []string{
			"topic0", "Data", "blockNum", "index",
		}
		topic0_target = "0x296ba4ca62c6c21c95e828080cb8aec7481b71390585605300a8a76f9e95b527"
	}

	if target_contract == "AAveLiquidation" {
		contract_address = "0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9"
		log_csv = "aave_liquidationcall_" + blcokFrom.String() + "_" + blockTo.String() + ".csv"
		log_headers = []string{
			"topic0", "topic1", "topic2", "topic3", "Data", "blockNum", "index",
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

			topics := make([]string, len(log_headers))
			// var topics [len_heder]string
			i := 0
			for i = range vLog.Topics {
				topics[i] = vLog.Topics[i].Hex()
				// fmt.Println(topics[i])
			}
			topics[i+1] = hex.EncodeToString(vLog.Data)
			topics[i+2] = strconv.FormatUint(uint64(vLog.BlockNumber), 10)
			topics[i+3] = strconv.FormatUint(uint64(vLog.Index), 10)
			log_writer.Write(topics[:])
			// log_r = append(
			// 	log_r,
			// 	topics[0],
			// 	topics[1],
			// 	topics[2],
			// 	topics[3],
			// )
		}

		// fmt.Println(topics[0]) // 0xe79e73da417710ae99aa2088575580a60415d359acfad9cdd3382d59c80281d4
	}

	// eventSignature := []byte("ItemSet(bytes32,bytes32)")
	// hash := crypto.Keccak256Hash(eventSignature)
	// fmt.Println(hash.Hex()) // 0xe79e73da417710ae99aa2088575580a60415d359acfad9cdd3382d59c80281d4
}
