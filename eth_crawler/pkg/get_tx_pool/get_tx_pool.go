package get_tx_pool

import (
	"context"
	"fmt"

	"github.com/ethereum/go-ethereum/rpc"
)

func Get_tx_pool_main() {
	archive_node := "http://localhost:19545"
	// save_file_path := "data/crawled/"

	// Create a client instance to connect to our providr
	// client, err := ethclient.Dial(archive_node)

	rpc, err := DialContext(archive_node)

	if err != nil {
		fmt.Println(err)
	}
	get_tx_pool(rpc)

}

func DialContext(rawurl string) (*rpc.Client, error) {
	c, err := rpc.DialContext(context.Background(), rawurl)
	if err != nil {
		return nil, err
	}
	return c, nil
}

func get_tx_pool(c *rpc.Client) {
	// var result map[string]string

	// var result map[string]string
	// ctx, cancel := context.WithTimeout(context.Background(), 10)
	// defer cancel()
	var result map[string]string
	err := c.CallContext(context.Background(), &result, "txpool_content")

	err = err

}
