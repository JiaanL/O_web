package csv_writer

import (
	"encoding/csv"
	"log"
	"os"
)

func Get_writer(save_file_path string, csv_file_name string, headers []string) (*os.File, *csv.Writer, []string) {
	file, _ := os.Create(save_file_path + csv_file_name)
	writer := csv.NewWriter(file)
	// write column headers
	writer.Write(headers)
	r := make([]string, 0, 1+len(headers))
	return file, writer, r
}

func ReadCsvFile(filePath string) [][]string {
	// reference : https://stackoverflow.com/questions/24999079/reading-csv-file-in-go
	f, err := os.Open(filePath)
	if err != nil {
		log.Fatal("Unable to read input file "+filePath, err)
	}
	defer f.Close()

	csvReader := csv.NewReader(f)
	records, err := csvReader.ReadAll()
	if err != nil {
		log.Fatal("Unable to parse file as CSV for "+filePath, err)
	}

	return records
}
