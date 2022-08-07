package type_define

type Tx struct {
	Hash, Value, From, To, Gas, Gas_price, Nonce string
}

type Receipt struct {
	Type, PostState, Status, CumulativeGasUsed, Bloom, TxHash, ContractAddress, GasUsed, BlockHash, BlockNumber, TransactionIndex string
}
