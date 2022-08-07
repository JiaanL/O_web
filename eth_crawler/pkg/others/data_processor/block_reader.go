package data_reader

// reference: https://hackernoon.com/create-an-api-to-interact-with-ethereum-blockchain-using-golang-part-1-sqf3z7z

import (
	"context"
	"fmt"
	"math/big"

	Models "eth_crawler/pkg/others/models"

	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/ethclient"
)

func GetBlockByNumber(client ethclient.Client, _blockNumber int64) *Models.Block {

	blockNumber := big.NewInt(_blockNumber)
	block, err := client.BlockByNumber(context.Background(), blockNumber)

	if err != nil {
		fmt.Println(err)
	}

	_block := &Models.Block{
		BlockNumber:       block.Number().Int64(),
		Timestamp:         block.Time(),
		Difficulty:        block.Difficulty().Uint64(),
		Hash:              block.Hash().String(),
		TransactionsCount: len(block.Transactions()),
		Transactions:      []Models.Transaction{},
	}

	for _, tx := range block.Transactions() {
		_block.Transactions = append(_block.Transactions, Models.Transaction{
			Hash:     tx.Hash().String(),
			Value:    tx.Value().String(),
			Gas:      tx.Gas(),
			GasPrice: tx.GasPrice().Uint64(),
			Nonce:    tx.Nonce(),
			To:       tx.To().String(),
		})
	}

	return _block
}

func GetTxByHash(client ethclient.Client, hash common.Hash) *Models.Transaction {

	defer func() {
		if err := recover(); err != nil {
			fmt.Println(err)
		}
	}()

	tx, pending, err := client.TransactionByHash(context.Background(), hash)

	if err != nil {
		fmt.Println(err)
	}

	return &Models.Transaction{
		Hash:     tx.Hash().String(),
		Value:    tx.Value().String(),
		Gas:      tx.Gas(),
		GasPrice: tx.GasPrice().Uint64(),
		To:       tx.To().String(),
		Pending:  pending,
		Nonce:    tx.Nonce(),
	}
}
