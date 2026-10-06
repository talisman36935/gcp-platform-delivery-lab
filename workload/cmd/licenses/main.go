// Collect redistribution notices for modules actually linked into the workload.
package main

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
)

type module struct{ Path, Version, Dir string }
type record struct {
	Path    string   `json:"module"`
	Version string   `json:"version"`
	Files   []string `json:"files"`
}

func main() {
	if err := collect(); err != nil {
		fmt.Fprintln(os.Stderr, "license collection failed:", err)
		os.Exit(1)
	}
}
func collect() error {
	if len(os.Args) != 2 {
		return fmt.Errorf("supply license output directory")
	}
	output := os.Args[1]
	if _, err := os.Stat(output); !os.IsNotExist(err) {
		return fmt.Errorf("output must not already exist")
	}
	if err := os.MkdirAll(output, 0755); err != nil {
		return err
	}
	standard, err := os.ReadFile(filepath.Join(runtime.GOROOT(), "LICENSE"))
	if err != nil {
		return err
	}
	if err = os.WriteFile(filepath.Join(output, "Go-LICENSE"), standard, 0644); err != nil {
		return err
	}
	command := exec.Command("go", "list", "-deps", "-json", "./cmd/workshop")
	stdout, err := command.StdoutPipe()
	if err != nil {
		return err
	}
	command.Stderr = os.Stderr
	if err = command.Start(); err != nil {
		return err
	}
	decoder := json.NewDecoder(stdout)
	seen := map[string]bool{}
	records := []record{}
	for {
		var pkg struct{ Module *module }
		err = decoder.Decode(&pkg)
		if err == io.EOF {
			break
		}
		if err != nil {
			_ = command.Process.Kill()
			_ = command.Wait()
			return err
		}
		m := pkg.Module
		if m == nil || m.Version == "" || seen[m.Path] {
			continue
		}
		seen[m.Path] = true
		directory := filepath.Join(output, strings.ReplaceAll(m.Path, "/", "_")+"@"+m.Version)
		entries, err := os.ReadDir(m.Dir)
		if err != nil {
			return err
		}
		files := []string{}
		for _, entry := range entries {
			name := strings.ToUpper(entry.Name())
			if entry.IsDir() || !(strings.HasPrefix(name, "LICENSE") || strings.HasPrefix(name, "NOTICE") || strings.HasPrefix(name, "COPYING")) {
				continue
			}
			data, err := os.ReadFile(filepath.Join(m.Dir, entry.Name()))
			if err != nil {
				return err
			}
			if err = os.MkdirAll(directory, 0755); err != nil {
				return err
			}
			if err = os.WriteFile(filepath.Join(directory, entry.Name()), data, 0644); err != nil {
				return err
			}
			files = append(files, entry.Name())
		}
		if len(files) == 0 {
			return fmt.Errorf("missing redistribution license for %s", m.Path)
		}
		records = append(records, record{m.Path, m.Version, files})
	}
	if err = command.Wait(); err != nil {
		return err
	}
	data, err := json.MarshalIndent(records, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(filepath.Join(output, "index.json"), append(data, '\n'), 0644)
}
