package decode_by_abi

// reference : https://github.com/huahuayu/go-transaction-decoder

import (
	"encoding/hex"
	"fmt"
	"log"
	"strings"

	"github.com/ethereum/go-ethereum/accounts/abi"
	"github.com/ethereum/go-ethereum/core/types"
)

func DecodeInput(tx *types.Transaction, router string) (funcName string, inputMap map[string]interface{}) {

	txInput := "0x" + hex.EncodeToString(tx.Data())

	funcName, inputMap = DecodeInputByStrHash(txInput, router)

	return
}

func DecodeLogEvent(logs []*types.Log, router string) {
	contractAbi, err := abi.JSON(strings.NewReader(router))
	if err != nil {
		log.Fatal(err)
	}

	for _, vLog := range logs {
		// event := struct {
		// 	Key   [32]byte
		// 	Value [32]byte
		// }{}
		fmt.Println(vLog.Data)
		event, err := contractAbi.Unpack("ItemSet", vLog.Data)
		if err != nil {
			log.Fatal(err)
		}
		fmt.Println(event)
		// fmt.Println(string(event.Key[:]))   // foo
		// fmt.Println(string(event.Value[:])) // bar

		var topics [4]string
		for i := range vLog.Topics {
			topics[i] = vLog.Topics[i].Hex()
		}

		fmt.Println(topics[0]) // 0xe79e73da417710ae99aa2088575580a60415d359acfad9cdd3382d59c80281d4
	}
}

func DecodeInputByStrHash(txInput string, router string) (funcName string, inputMap map[string]interface{}) {
	// reference : https://github.com/huahuayu/go-transaction-decoder

	// load contract ABI
	abi, err := abi.JSON(strings.NewReader(router))
	if err != nil {
		log.Fatal(err)
	}

	// decode txInput method signature
	decodedSig, err := hex.DecodeString(txInput[2:10])
	if err != nil {
		log.Fatal(err)
	}

	// recover Method from signature and ABI
	method, err := abi.MethodById(decodedSig)
	if err != nil {
		log.Fatal(err)
	}

	funcName = method.Name

	// decode txInput Payload
	decodedData, err := hex.DecodeString(txInput[10:])
	if err != nil {
		log.Fatal(err)
	}

	// unpack method inputs
	inputMap = make(map[string]interface{}, 0)
	err = method.Inputs.UnpackIntoMap(inputMap, decodedData)
	if err != nil {
		log.Fatal(err)
	}

	return
}
