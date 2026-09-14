package corpus

import (
	"bytes"
	"encoding/json"
	"fmt"
	"sort"
	"unicode/utf16"
)

// canonical matches the ASCII-escaped, sorted JSON used by corpus snapshot v1.
func canonical(value any) ([]byte, error) {
	encoded, err := json.Marshal(value)
	if err != nil {
		return nil, err
	}
	decoder := json.NewDecoder(bytes.NewReader(encoded))
	decoder.UseNumber()
	var generic any
	if err := decoder.Decode(&generic); err != nil {
		return nil, err
	}
	var out bytes.Buffer
	var write func(any) error
	writeString := func(s string) {
		out.WriteByte('"')
		for _, r := range s {
			switch r {
			case '"', '\\':
				out.WriteByte('\\')
				out.WriteRune(r)
			case '\b':
				out.WriteString(`\b`)
			case '\f':
				out.WriteString(`\f`)
			case '\n':
				out.WriteString(`\n`)
			case '\r':
				out.WriteString(`\r`)
			case '\t':
				out.WriteString(`\t`)
			default:
				if r < 0x20 || r >= 0x7f {
					if r <= 0xffff {
						fmt.Fprintf(&out, `\u%04x`, r)
					} else {
						hi, lo := utf16.EncodeRune(r)
						fmt.Fprintf(&out, `\u%04x\u%04x`, hi, lo)
					}
				} else {
					out.WriteRune(r)
				}
			}
		}
		out.WriteByte('"')
	}
	write = func(v any) error {
		switch v := v.(type) {
		case nil:
			out.WriteString("null")
		case bool:
			if v {
				out.WriteString("true")
			} else {
				out.WriteString("false")
			}
		case json.Number:
			out.WriteString(string(v))
		case string:
			writeString(v)
		case []any:
			out.WriteByte('[')
			for i, item := range v {
				if i > 0 {
					out.WriteByte(',')
				}
				if err := write(item); err != nil {
					return err
				}
			}
			out.WriteByte(']')
		case map[string]any:
			keys := make([]string, 0, len(v))
			for key := range v {
				keys = append(keys, key)
			}
			sort.Strings(keys)
			out.WriteByte('{')
			for i, key := range keys {
				if i > 0 {
					out.WriteByte(',')
				}
				writeString(key)
				out.WriteByte(':')
				if err := write(v[key]); err != nil {
					return err
				}
			}
			out.WriteByte('}')
		default:
			return fmt.Errorf("unsupported canonical JSON value %T", v)
		}
		return nil
	}
	if err := write(generic); err != nil {
		return nil, err
	}
	return out.Bytes(), nil
}
