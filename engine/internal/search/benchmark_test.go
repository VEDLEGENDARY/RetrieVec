package search

import("context";"fmt";"testing";"retrievallab/engine/internal/corpus";"retrievallab/engine/internal/index";"retrievallab/engine/internal/scoring")

func BenchmarkSearch(b *testing.B){
 docs:=make([]corpus.Document,1000);for i:=range docs{docs[i]=corpus.Document{Chunk:corpus.Chunk{ChunkID:fmt.Sprintf("c%06d",i),PaperID:"p",PaperVersionID:"v",CollectionID:"c",Text:fmt.Sprintf("retrieval red red blue term%d",i%17)}}}
 idx,err:=index.Build(docs);if err!=nil{b.Fatal(err)};b.ReportAllocs();b.ResetTimer()
 for b.Loop(){if _,err:=Execute(context.Background(),idx,Request{Query:`"red red" AND retrieval`,Mode:"structured",TopK:10},scoring.Default());err!=nil{b.Fatal(err)}}
}
