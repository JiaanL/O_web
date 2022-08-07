package models

// reference: https://hackernoon.com/create-an-api-to-interact-with-ethereum-blockchain-using-golang-part-1-sqf3z7z

// Block data structure
type Block struct {
	BlockNumber       int64         `json:"blockNumber"`
	Timestamp         uint64        `json:"timestamp"`
	Difficulty        uint64        `json:"difficulty"`
	Hash              string        `json:"hash"`
	TransactionsCount int           `json:"transactionsCount"`
	Transactions      []Transaction `json:"transactions"`
}

// Transaction data structure
type Transaction struct {
	Hash     string `json:"hash"`
	Value    string `json:"value"`
	Gas      uint64 `json:"gas"`
	GasPrice uint64 `json:"gasPrice"`
	Nonce    uint64 `json:"nonce"`
	To       string `json:"to"`
	Pending  bool   `json:"pending"`
}
