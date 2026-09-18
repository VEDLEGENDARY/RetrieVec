package segment
import("bytes";"crypto/sha256";"encoding/binary";"testing";"retrievallab/engine/internal/corpus";"retrievallab/engine/internal/index")
func TestGoldenOneToken(t *testing.T){
 idx,err:=index.Build([]corpus.Document{{Chunk:corpus.Chunk{ChunkID:"a",PaperID:"p",PaperVersionID:"v",CollectionID:"c",Text:"x"}}});if err!=nil{t.Fatal(err)};got,err:=Encode(idx);if err!=nil{t.Fatal(err)}
 // Independent one-chunk/one-term fixture: table 3 bytes, dictionary 19, posting 3.
 want:=make([]byte,96);copy(want,"RLSEG001");want[8]=1;want[12]=96
 for offset,value:=range map[int]uint64{16:153,24:1,32:1,40:96,48:99,56:118,64:121,72:1}{binary.LittleEndian.PutUint64(want[offset:],value)}
 want=append(want,1,'a',1,1,'x',1);want=binary.LittleEndian.AppendUint64(want,118);want=binary.LittleEndian.AppendUint64(want,3);want=append(want,0,1,0);checksum:=sha256.Sum256(want);want=append(want,checksum[:]...)
 if !bytes.Equal(got,want){t.Fatalf("golden mismatch %x != %x",got,want)}
}
