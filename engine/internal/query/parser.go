package query

import (
	"fmt"
	"retrievallab/engine/internal/analysis"
	"sort"
	"unicode"
	"unicode/utf8"
)

type Node struct {
	Kind        string
	Terms       []string
	Left, Right *Node
}
type Error struct {
	Message  string
	Position int
}

func (e *Error) Error() string { return fmt.Sprintf("%s at character %d", e.Message, e.Position) }

type token struct {
	kind, text string
	position   int
}
type parser struct {
	tokens []token
	at     int
}

func lex(input string) ([]token, error) {
	if !utf8.ValidString(input) || utf8.RuneCountInString(input) > 4096 {
		return nil, &Error{"invalid query length or encoding", 0}
	}
	chars := []rune(input)
	result := []token{}
	for i := 0; i < len(chars); {
		if unicode.IsSpace(chars[i]) {
			i++
			continue
		}
		start := i
		switch chars[i] {
		case '(', ')':
			result = append(result, token{string(chars[i]), "", start})
			i++
		case '"':
			i++
			value := []rune{}
			closed := false
			for i < len(chars) {
				c := chars[i]
				i++
				if c == '"' {
					closed = true
					break
				}
				if c == '\\' {
					if i == len(chars) || (chars[i] != '"' && chars[i] != '\\') {
						return nil, &Error{"invalid escape", i - 1}
					}
					c = chars[i]
					i++
				}
				value = append(value, c)
			}
			if !closed {
				return nil, &Error{"unterminated phrase", start}
			}
			result = append(result, token{"phrase", string(value), start})
		default:
			for i < len(chars) && !unicode.IsSpace(chars[i]) && chars[i] != '(' && chars[i] != ')' && chars[i] != '"' {
				if chars[i] == '\\' {
					return nil, &Error{"escape outside phrase", i}
				}
				i++
			}
			value := string(chars[start:i])
			kind := "term"
			if value == "AND" || value == "OR" || value == "NOT" {
				kind = value
			}
			result = append(result, token{kind, value, start})
		}
		if len(result) > 256 {
			return nil, &Error{"too many parser tokens", start}
		}
	}
	result = append(result, token{"end", "", len(chars)})
	return result, nil
}

func Parse(input string) (*Node, error) {
	tokens, err := lex(input)
	if err != nil {
		return nil, err
	}
	p := parser{tokens: tokens}
	node, err := p.expression(0, 0)
	if err != nil {
		return nil, err
	}
	if p.peek().kind != "end" {
		return nil, &Error{"expected explicit operator", p.peek().position}
	}
	if len(PositiveTerms(node)) == 0 {
		return nil, &Error{"query has no positive terms", 0}
	}
	return node, nil
}
func (p *parser) peek() token { return p.tokens[p.at] }
func (p *parser) expression(minimum, depth int) (*Node, error) {
	left, err := p.unary(depth)
	if err != nil {
		return nil, err
	}
	for {
		op := p.peek()
		precedence := 0
		if op.kind == "OR" {
			precedence = 1
		}
		if op.kind == "AND" {
			precedence = 2
		}
		if precedence == 0 || precedence < minimum {
			break
		}
		p.at++
		right, err := p.expression(precedence+1, depth)
		if err != nil {
			return nil, err
		}
		left = &Node{Kind: op.kind, Left: left, Right: right}
	}
	return left, nil
}
func (p *parser) unary(depth int) (*Node, error) {
	t := p.peek()
	if depth > 32 {
		return nil, &Error{"nesting limit exceeded", t.position}
	}
	switch t.kind {
	case "NOT":
		p.at++
		child, err := p.unary(depth + 1)
		return &Node{Kind: "NOT", Left: child}, err
	case "(":
		p.at++
		child, err := p.expression(0, depth+1)
		if err != nil {
			return nil, err
		}
		if p.peek().kind != ")" {
			return nil, &Error{"expected closing parenthesis", p.peek().position}
		}
		p.at++
		return child, nil
	case "term", "phrase":
		p.at++
		tokens, err := analysis.Analyze(t.text)
		if err != nil {
			return nil, err
		}
		if len(tokens) == 0 || (t.kind == "term" && len(tokens) != 1) || len(tokens) > 256 {
			return nil, &Error{"invalid term or phrase length", t.position}
		}
		terms := make([]string, len(tokens))
		for i, v := range tokens {
			terms[i] = v.Term
		}
		return &Node{Kind: t.kind, Terms: terms}, nil
	default:
		return nil, &Error{"expected term, phrase, NOT, or parenthesis", t.position}
	}
}

// PositiveTerms collects unique terms below an even number of NOT nodes.
func PositiveTerms(node *Node) []string {
	set := map[string]bool{}
	var walk func(*Node, bool)
	walk = func(n *Node, positive bool) {
		if n == nil {
			return
		}
		if n.Kind == "NOT" {
			walk(n.Left, !positive)
			return
		}
		if positive {
			for _, term := range n.Terms {
				set[term] = true
			}
		}
		walk(n.Left, positive)
		walk(n.Right, positive)
	}
	walk(node, true)
	result := make([]string, 0, len(set))
	for term := range set {
		result = append(result, term)
	}
	sort.Strings(result)
	return result
}
