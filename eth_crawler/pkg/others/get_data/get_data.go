package get_data

// reference : https://hackernoon.com/create-an-api-to-interact-with-ethereum-blockchain-using-golang-part-1-sqf3z7z

import (
	"context"
	TypeDefine "eth_crawler/pkg/type_define"
	"fmt"
	"log"
	"math/big"
	"strconv"

	"github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/ethclient"
)

func GetLatestBlock(client *ethclient.Client) *types.Block {
	// get the latest block data
	header, _ := client.HeaderByNumber(context.Background(), nil)
	blockNumber := big.NewInt(header.Number.Int64())
	block, err := client.BlockByNumber(context.Background(), blockNumber)
	if err != nil {
		fmt.Println(err)
	}

	// for _, tx := range block.Transactions() {
	// 	fmt.Println(tx)
	// }
	// fmt.Println("------------------------")

	return block
}

func ExtractInfo(client *ethclient.Client, tx *types.Transaction, router string) (TypeDefine.Tx, TypeDefine.Receipt) {

	chainID, err := client.NetworkID(context.Background())
	if err != nil {
		log.Fatal(err)
	}

	msg, err := tx.AsMessage(types.NewEIP155Signer(chainID), nil)
	if err != nil {
		log.Fatal(err)
	}
	tx_from := msg.From().Hex()

	receipt, err := client.TransactionReceipt(context.Background(), tx.Hash())
	if err != nil {
		log.Fatal(err)
	}

	// fmt.Printf("%+v\n", receipt.Logs)

	// DecodeByABI.DecodeLogEvent(receipt.Logs, router)

	tx_info := TypeDefine.Tx{
		Hash:      tx.Hash().Hex(),
		Value:     tx.Value().String(),
		Gas:       strconv.FormatUint(tx.Gas(), 10),
		Gas_price: strconv.FormatUint(tx.GasPrice().Uint64(), 10),
		Nonce:     strconv.FormatUint(tx.Nonce(), 10),
		From:      tx_from,
		To:        tx.To().Hex(),
	}

	my_receipt := TypeDefine.Receipt{
		Type:              strconv.FormatUint(uint64(receipt.Type), 10),
		PostState:         string(receipt.PostState),
		Status:            strconv.FormatUint(receipt.Status, 10),
		CumulativeGasUsed: strconv.FormatUint(receipt.CumulativeGasUsed, 10),
		Bloom:             strconv.FormatUint(receipt.Bloom.Big().Uint64(), 10),
		// Logs:              string(receipt.Logs),
		TxHash:          receipt.TxHash.Hex(),
		ContractAddress: receipt.ContractAddress.Hex(),
		GasUsed:         strconv.FormatUint(receipt.GasUsed, 10),
		// Inclusion information: These fields provide information about the inclusion of the
		// transaction corresponding to this receipt.
		BlockHash:        receipt.BlockHash.Hex(),
		BlockNumber:      strconv.FormatUint(receipt.BlockNumber.Uint64(), 10),
		TransactionIndex: strconv.FormatUint(uint64(receipt.TransactionIndex), 10),
	}
	// fmt.Printf("%+v\n", receipt.Logs)
	return tx_info, my_receipt
}
