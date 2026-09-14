// Command retrievald is the entry point for the local retrieval service.
package main

import (
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
)

const version = "0.1.0"

func main() {
	os.Exit(run(os.Args[1:], os.Stdout, os.Stderr))
}

func run(args []string, stdout, stderr io.Writer) int {
	if len(args) > 0 && args[0] == "analyze" {
		if len(args) != 1 {
			fmt.Fprintln(stderr, "analyze: no arguments expected")
			return 2
		}
		return analyzeCommand(os.Stdin, stdout, stderr)
	}
	flags := flag.NewFlagSet("retrievald", flag.ContinueOnError)
	flags.SetOutput(stderr)
	showVersion := flags.Bool("version", false, "print the version and exit")
	flags.Usage = func() {
		fmt.Fprintln(stderr, "Usage: retrievald [--version] | analyze")
		fmt.Fprintln(stderr, "Workspace scaffold; HTTP serving is planned for step 9.")
		flags.PrintDefaults()
	}
	if err := flags.Parse(args); err != nil {
		if errors.Is(err, flag.ErrHelp) {
			return 0
		}
		return 2
	}
	if flags.NArg() != 0 {
		fmt.Fprintln(stderr, "retrievald: unexpected positional arguments")
		return 2
	}
	if *showVersion {
		fmt.Fprintln(stdout, "retrievald "+version)
		return 0
	}
	fmt.Fprintln(stderr, "retrievald: HTTP serving is not implemented yet; use --help")
	return 2
}
