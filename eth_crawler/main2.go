package main

import (
	"context"
	"encoding/hex"
	"fmt"
	"log"
	"math"
	"math/big"
	"strconv"
	"sync"

	"github.com/ethereum/go-ethereum"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/ethclient" // GetTxPool "eth_crawler/pkg/get_tx_pool"
	// "github.com/ethereum/go-ethereum/eth/tracers"
	// GetTx "eth_crawler/pkg/get_tx"
	// CallContract "eth_crawler/pkg/call_contract"
)

import "C"

type jsonError struct {
	Code    int         `json:"code"`
	Message string      `json:"message"`
	Data    interface{} `json:"data,omitempty"`
}

func (err *jsonError) Error() string {
	if err.Message == "" {
		return fmt.Sprintf("json-rpc error %d", err.Code)
	}
	return err.Message
}

func (err *jsonError) ErrorCode() int {
	return err.Code
}

func (err *jsonError) ErrorData() interface{} {
	return err.Data
}

func main() {
	// GetLog.Get_log_data_main()
	// GetLog.Get_log_source_data_main()
	// GetBlock.Get_block_data_main()
	// GetTxPool.Get_tx_pool_main()
	// GetTx.Get_multi_wallet_tx_main()
	// CallContract.CallContract()

	// GetTx.Get_tx_to_target_contract_main()
	// target_contract := "chainlink_eth_usd"

	archive_node := "http://localhost:19545"

	blcokFrom := 14722000
	blockTo := 14722214

	// get_block_time(C.CString(archive_node), blcokFrom, blockTo)
	target_contract := "chainlink_usdt_eth"
	target_contract_c := C.CString(target_contract)
	return_data := get_log_data(target_contract_c, C.CString(archive_node), blcokFrom, blockTo)
	fmt.Println(C.GoString(return_data))
	// ttt := get_aave_log(C.CString(archive_node), blcokFrom, blockTo)
	// fmt.Println(ttt)
	// file, err := os.Create("aave.txt")
	// if err != nil {
	// 	fmt.Println(err)
	// } else {
	// 	file.WriteString(ttt)
	// 	fmt.Println("Done")
	// }
	// file.Close()
}

// type ChainlinkOracleLogData struct {
// 	Topic0, Current, RoundId, UpdatedAt, BlockNum, Index string
// }

// type MakerMedianLogData struct {
// 	Topic0, Data, BlockNum, Index string
// }

// type AaveLiquidationLogData struct {
// 	Topic0, Topic1, Topic2, Topic3, Data, BlockNum, Index string
// }

// type UniswapV2LogData struct {
// 	Topic0, Reserve0, Reserve1, BlockNum, Index string
// }

// type UniswapV3LogData struct {
// 	Topic0, Topic1, Topic2, Data, BlockNum, Index string
// }

// func createValue(header string) interface{} {
// 	switch header {
// 	case "ChainLink_ETH_USD", "ChainLink_DAI_ETH", "ChainLink_USDT_ETH", "ChainLink_USDC_ETH":
// 		d := new(ChainlinkOracleLogData)
// 		return d
// 	case "UniswapV2_USDT_ETH", "UniswapV2_USDC_ETH":
// 		d := new(UniswapV2LogData)
// 		return d
// 	case "UniswapV3_USDC_ETH_03", "UniswapV3_USDC_ETH_005":
// 		d := new(UniswapV3LogData)
// 		return d
// 	case "MakerDAO_ETH_USD_Median":
// 		d := new(MakerMedianLogData)
// 		return d
// 	case "AAveLiquidation":
// 		d := new(AaveLiquidationLogData)
// 		return d
// 	default:
// 		return nil
// 	}
// }

//export get_latest_block_num
func get_latest_block_num(archive_node_c *C.char) int {
	archive_node := C.GoString(archive_node_c)
	client, err := ethclient.Dial(archive_node)
	if err != nil {
		log.Fatal(err)
	}
	ctx := context.Background()
	header, err := client.HeaderByNumber(ctx, nil)
	if err != nil {
		log.Fatal(err)
	}
	return int(header.Number.Int64())
}

//export get_log_data
func get_log_data(target_contract_c *C.char, archive_node_c *C.char, block_from int, block_to int) *C.char {

	target_contract := C.GoString(target_contract_c)
	archive_node := C.GoString(archive_node_c)

	var contract_address string
	var log_headers []string
	var topic0_target string

	blockFrom := big.NewInt(int64(block_from))
	blockTo := big.NewInt(int64(block_to))

	if target_contract == "chainlink_eth_usd" {
		// fmt.Println(target_contract)
		contract_address = "0x37bC7498f4FF12C19678ee8fE19d713b87F6a9e6"
		if blockFrom.Int64() < 12453812 {
			contract_address = "0xd3fcd40153e56110e6eeae13e12530e26c9cb4fd"
		}
		log_headers = []string{
			"Topic0", "Current", "RoundId", "UpdatedAt", "BlockNum", "Index",
		}
		topic0_target = "0x0559884fd3a460db3073b7fc896cc77986f16e378210ded43186175bf646fc5f"
	}
	// USD / ETH not support

	if target_contract == "chainlink_dai_eth" {
		contract_address = "0x158228e08C52F3e2211Ccbc8ec275FA93f6033FC"
		log_headers = []string{
			"Topic0", "Current", "RoundId", "UpdatedAt", "BlockNum", "Index",
		}
		topic0_target = "0x0559884fd3a460db3073b7fc896cc77986f16e378210ded43186175bf646fc5f"
	}
	// ETH / DAI not support

	if target_contract == "chainlink_usdt_eth" {
		contract_address = "0x7de0d6fce0c128395c488cb4df667cdbfb35d7de"
		log_headers = []string{
			"Topic0", "Current", "RoundId", "UpdatedAt", "BlockNum", "Index",
		}
		topic0_target = "0x0559884fd3a460db3073b7fc896cc77986f16e378210ded43186175bf646fc5f"
	}
	// ETH / USDT not support

	if target_contract == "chainlink_usdc_eth" {
		contract_address = "0xe5BbBdb2Bb953371841318E1Edfbf727447CeF2E"
		log_headers = []string{
			"Topic0", "Current", "RoundId", "UpdatedAt", "BlockNum", "Index",
		}
		topic0_target = "0x0559884fd3a460db3073b7fc896cc77986f16e378210ded43186175bf646fc5f"
	}
	// ETH / USDC not support

	// if target_contract == "ChainlinkOnChainAGG" {
	// 	contract_address = "0x00c7A37B03690fb9f41b5C5AF8131735C7275446"
	// 	log_headers = []string{
	// 		"Topic0", "Current", "RoundId", "UpdatedAt", "BlockNum", "Index",
	// 	}
	// 	topic0_target = "0x0559884fd3a460db3073b7fc896cc77986f16e378210ded43186175bf646fc5f"
	// }

	if target_contract == "uniswapv2_usdt_eth" || target_contract == "uniswapv2_eth_usdt" {
		contract_address = "0x0d4a11d5eeaac28ec3f61d100daf4d40471f1852"
		log_headers = []string{
			"Topic0", "Data", "BlockNum", "Index",
		}
		topic0_target = "0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1"
	}

	if target_contract == "uniswapv2_usdc_eth" || target_contract == "uniswapv2_eth_usdc" {
		contract_address = "0xb4e16d0168e52d35cacd2c6185b44281ec28c9dc"
		log_headers = []string{
			"Topic0", "Data", "BlockNum", "Index",
		}
		topic0_target = "0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1"
	}

	if target_contract == "uniswapv2_dai_eth" || target_contract == "uniswapv2_eth_dai" {
		contract_address = "0xA478c2975Ab1Ea89e8196811F51A7B7Ade33eB11"
		log_headers = []string{
			"Topic0", "Data", "BlockNum", "Index",
		}
		topic0_target = "0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1"
	}

	// if target_contract == "UniswapV3_USDC_ETH_03" {
	// 	contract_address = "0x8ad599c3A0ff1De082011EFDDc58f1908eb6e6D8"
	// 	log_headers = []string{
	// 		"Topic0", "Topic1", "Topic2", "Data", "BlockNum", "Index",
	// 	}
	// 	topic0_target = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"
	// }

	// target_contract == "UniswapV3_USDC_ETH_005"
	if target_contract == "uniswapv3_usdc_eth" || target_contract == "uniswapv3_eth_usdc" {
		contract_address = "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640"
		log_headers = []string{
			"Topic0", "Topic1", "Topic2", "Data", "BlockNum", "Index",
		}
		topic0_target = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"
	}

	// if target_contract == "UniswapV3_USDT_ETH_03" {
	// 	contract_address = "0x4e68Ccd3E89f51C3074ca5072bbAC773960dFa36"
	// 	log_headers = []string{
	// 		"Topic0", "Topic1", "Topic2", "Data", "BlockNum", "Index",
	// 	}
	// 	topic0_target = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"
	// }

	// UniswapV3_USDT_ETH_005
	if target_contract == "uniswapv3_usdt_eth" || target_contract == "uniswapv3_eth_usdt" {
		contract_address = "0x11b815efB8f581194ae79006d24E0d814B7697F6"
		log_headers = []string{
			"Topic0", "Topic1", "Topic2", "Data", "BlockNum", "Index",
		}
		topic0_target = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"
	}

	// UniswapV3_DAI_ETH_005
	if target_contract == "uniswapv3_dai_eth" || target_contract == "uniswapv3_eth_dai" {
		contract_address = "0x60594a405d53811d3BC4766596EFD80fd545A270"
		log_headers = []string{
			"Topic0", "Topic1", "Topic2", "Data", "BlockNum", "Index",
		}
		topic0_target = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"
	}

	// _Median
	if target_contract == "maker_eth_usd" {
		contract_address = "0x64DE91F5A373Cd4c28de3600cB34C7C6cE410C85"
		log_headers = []string{
			"Topic0", "Data", "BlockNum", "Index",
		}
		topic0_target = "0xb78ebc573f1f889ca9e1e0fb62c843c836f3d3a2e1f43ef62940e9b894f4ea4c"
	}

	// if target_contract == "MakerDAO_ETH_USD_OSM" {
	// 	contract_address = "0x81FE72B5A8d1A857d176C3E7d5Bd2679A9B85763"
	// 	log_headers = []string{
	// 		"topic0", "Data", "blockNum", "index",
	// 	}
	// 	topic0_target = "0x296ba4ca62c6c21c95e828080cb8aec7481b71390585605300a8a76f9e95b527"
	// }

	if target_contract == "aave_liquidation" {
		contract_address = "0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9"
		log_headers = []string{
			"topic0", "topic1", "topic2", "topic3", "Data", "blockNum", "index",
		}
		topic0_target = "0xe413a321e8681d831f4dbccbca790d2952b56f977908e45be37335533e005286"
	}

	if target_contract == "aave_deposit" {
		contract_address = "0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9"
		log_headers = []string{
			"topic0", "topic1", "topic2", "topic3", "Data", "blockNum", "index",
		}
		topic0_target = "0xde6857219544bb5b7746f48ed30be6386fefc61b2f864cacf559893bf50fd951"
	}

	if target_contract == "aave_withdraw" {
		contract_address = "0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9"
		log_headers = []string{
			"topic0", "topic1", "topic2", "topic3", "Data", "blockNum", "index",
		}
		topic0_target = "0x3115d1449a7b732c986cba18244e897a450f61e1bb8d589cd2e69e6c8924f9f7"
	}

	if target_contract == "aave_repay" {
		contract_address = "0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9"
		log_headers = []string{
			"topic0", "topic1", "topic2", "topic3", "Data", "blockNum", "index",
		}
		topic0_target = "0x4cdde6e09bb755c9a5589ebaec640bbfedff1362d4b255ebf8339782b9942faa"
	}

	if target_contract == "aave_borrow" {
		contract_address = "0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9"
		log_headers = []string{
			"topic0", "topic1", "topic2", "topic3", "Data", "blockNum", "index",
		}
		topic0_target = "0xc6a898309e823ee50bac64e45ca8adba6690e99e7841c45d754e2a38e9019d9b"
	}

	if target_contract == "aave_reserve_update" {
		contract_address = "0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9"
		log_headers = []string{
			"topic0", "topic1", "Data", "blockNum", "index",
		}
		topic0_target = "0x804c9b842b2748a22bb64b345453a3de7ca54a6ca45ce00d415894979e22897a"
	}

	if target_contract == "aave_reserve_as_collateral_enabled" {
		contract_address = "0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9"
		log_headers = []string{
			"topic0", "topic1", "topic2", "Data", "blockNum", "index",
		}
		topic0_target = "0x00058a56ea94653cdf4f152d227ace22d4c00ad99e2a43f58cb7d9e3feb295f2"
	}

	if contract_address == "" {
		return C.CString("Not support")
	}

	// Create a client instance to connect to our providr
	client, err := ethclient.Dial(archive_node)
	if err != nil {
		fmt.Println(err)
	}

	contractAddress := common.HexToAddress(contract_address)
	query := ethereum.FilterQuery{
		FromBlock: blockFrom,
		ToBlock:   blockTo, //(12466826 + 100), //14838875),
		Addresses: []common.Address{
			contractAddress,
		},
	}
	logs, err := client.FilterLogs(context.Background(), query)

	// if err != nil {
	// 	// var data = new(jsonError)
	// 	var data *jsonError
	// 	// As - 解析错误内容
	// 	if errors.As(err, &data) {
	// 		if data.Code == -32000 {
	// 			block_from += 1
	// 			blockFrom := big.NewInt(int64(block_from))
	// 			query := ethereum.FilterQuery{
	// 				FromBlock: blockFrom,
	// 				ToBlock:   blockTo, //(12466826 + 100), //14838875),
	// 				Addresses: []common.Address{
	// 					contractAddress,
	// 				},
	// 			}
	// 			_, err := client.FilterLogs(context.Background(), query)
	// 			err = err
	// 		}
	// 	}
	// }

	if err != nil {
		log.Fatal(err)
	}

	all_data_str := ""

	for _, vLog := range logs {

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

			data_str := `{`

			for i, s := range topics {
				data_str += `"` + log_headers[i] + `":"` + s + `"`
				if i < len(topics)-1 {
					data_str += `,`
				}
			}

			data_str += `};`

			all_data_str += data_str
			// kkk := `{"ID":"abc","Content":[1,2,3]}`

			// data := createValue(target_contract)
			// if err := json.Unmarshal([]byte(data_str), data); err != nil {
			// 	panic(err)
			// }

			// kkk = kkk

			// fmt.Println(all_data_str_array)

		}

	}
	return C.CString(all_data_str)

}

// func get_aave_log(archive_node_c *C.char, block_from int, block_to int) string {

//export get_aave_log
func get_aave_log(archive_node_c *C.char, block_from int, block_to int) *C.char {

	// target_contract := C.GoString(target_contract_c)
	archive_node := C.GoString(archive_node_c)

	var contract_address string
	// var log_headers []string
	// var topic0_target string

	blockFrom := big.NewInt(int64(block_from))
	blockTo := big.NewInt(int64(block_to))

	contract_address = "0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9"

	// Create a client instance to connect to our providr
	client, err := ethclient.Dial(archive_node)
	if err != nil {
		fmt.Println(err)
	}

	contractAddress := common.HexToAddress(contract_address)
	query := ethereum.FilterQuery{
		FromBlock: blockFrom,
		ToBlock:   blockTo, //(12466826 + 100), //14838875),
		Addresses: []common.Address{
			contractAddress,
		},
	}
	logs, err := client.FilterLogs(context.Background(), query)

	if err != nil {
		log.Fatal(err)
	}

	all_data_str := ""

	for _, vLog := range logs {

		topics := make([]string, len(vLog.Topics)+3)
		log_headers := make([]string, len(vLog.Topics)+3)
		// var topics [len_heder]string
		i := 0
		for i = range vLog.Topics {
			topics[i] = vLog.Topics[i].Hex()
			log_headers[i] = "Topic" + strconv.Itoa(i)
			// fmt.Println(topics[i])
		}
		topics[i+1] = hex.EncodeToString(vLog.Data)
		log_headers[i+1] = "Data"
		topics[i+2] = strconv.FormatUint(uint64(vLog.BlockNumber), 10)
		log_headers[i+2] = "BlockNumber"
		topics[i+3] = strconv.FormatUint(uint64(vLog.Index), 10)
		log_headers[i+3] = "Index"

		data_str := `{`

		for i, s := range topics {
			data_str += `"` + log_headers[i] + `":"` + s + `"`
			if i < len(topics)-1 {
				data_str += `,`
			}
		}

		data_str += `};`

		all_data_str += data_str

	}
	// return all_data_str
	return C.CString(all_data_str)

}

//export get_single_block_time
func get_single_block_time(archive_node_c *C.char, block_num int) *C.char {
	archive_node := C.GoString(archive_node_c)
	blockNum := big.NewInt(int64(block_num))

	client, err := ethclient.Dial(archive_node)
	if err != nil {
		log.Fatal(err)
	}

	header, err := client.HeaderByNumber(context.Background(), blockNum)
	if err != nil {
		log.Fatal(err)
	}

	block_data := `{` + `"` + header.Number.String() + `":"` + strconv.FormatUint(uint64(header.Time), 10) + `"` + `}`

	return C.CString(block_data)
}

//export get_block_time
func get_block_time(archive_node_c *C.char, block_from int, block_to int) *C.char {
	archive_node := C.GoString(archive_node_c)

	// blockFrom := big.NewInt(int64(block_from))
	// blockTo := big.NewInt(int64(block_to))

	// client, err := ethclient.Dial(archive_node)
	// if err != nil {
	// 	log.Fatal(err)
	// }

	blockNumber := block_from
	blockMax := block_to

	// Multi Process
	p_num := 10

	c := make(chan [][2]string, p_num*2)
	wg := &sync.WaitGroup{}

	var block_data_array [][2]string

	counter := 0

	each_gap := int(math.Ceil((float64(block_to) - float64(block_from)) / float64(p_num)))

	for blockNumber <= blockMax {
		wg.Add(1)
		go get_multiple_block_info(archive_node, blockNumber, blockNumber+each_gap, wg, c)
		counter++
		blockNumber += each_gap
	}
	wg.Wait()
	for i := 0; i < counter; i++ {
		block_data_array = append(block_data_array, <-c...)
	}

	data_str := `{`
	for i, block_data := range block_data_array {
		data_str += `"` + block_data[0] + `":"` + block_data[1] + `"`
		if i < len(block_data_array)-1 {
			data_str += `,`
		}
	}

	data_str += `}`

	return C.CString(data_str)
}

func get_multiple_block_info(archive_node string, block_from int, block_to int, wg *sync.WaitGroup, c chan [][2]string) {
	defer wg.Done()

	blockFrom := big.NewInt(int64(block_from))
	blockTo := big.NewInt(int64(block_to))

	client, err := ethclient.Dial(archive_node)
	if err != nil {
		log.Fatal(err)
	}

	blockNumber := blockFrom.Uint64()
	blockMax := blockTo.Uint64()

	var block_data_array [][2]string

	for blockNumber <= blockMax {

		header, err := client.HeaderByNumber(context.Background(), big.NewInt(int64(blockNumber)))
		if err != nil {
			log.Fatal(err)
		}

		var block_data [2]string
		block_data[0] = header.Number.String()
		block_data[1] = strconv.FormatUint(uint64(header.Time), 10)

		block_data_array = append(block_data_array, block_data)

		blockNumber = blockNumber + 1

	}
	c <- block_data_array
}
