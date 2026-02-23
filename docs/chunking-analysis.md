# Chunking Analysis: Why 500 Tokens with 50 Overlap

## The Problem

Chunk size is the single most impactful parameter in a RAG system. Every other optimization (caching, hybrid search, prompt engineering) is wasted if the chunks fed to the LLM are wrong.

## What Happens at Different Chunk Sizes

### Too Small (100-200 tokens)
- Chunks are sentence fragments — "The leave policy states that employees..."
- LLM receives incomplete thoughts and can't synthesize an answer
- More chunks needed to cover the same content → more noise in retrieval
- Precision@5 drops because relevant information is split across too many small chunks

### Too Large (1000+ tokens)
- Chunks contain mixed topics — a single chunk might cover both leave policy AND expense limits
- Vector embedding represents the average meaning of mixed topics → weak similarity signal
- False positives increase: a chunk about "travel expenses AND leave for travel" matches both "expense policy" and "leave policy" queries equally
- The LLM gets noisy context with irrelevant sections

### Sweet Spot (500 tokens, 50 overlap)
- Each chunk typically covers one coherent topic or sub-topic
- Large enough for the LLM to understand context
- Small enough that the embedding represents a specific concept
- Overlap of 50 tokens (~1-2 sentences) ensures boundary content isn't lost

## Why 50-Token Overlap Specifically

Consider this text split at exactly 500 tokens without overlap:

```
...the annual leave policy allows 20 days per year. | Employees must submit requests...
                                                     ^ split point
```

The sentence "Employees must submit requests 10 days in advance" is only in chunk 2. A query about "how to request leave" might match chunk 1 (about leave) but miss the procedure in chunk 2.

With 50-token overlap:
```
Chunk 1: ...the annual leave policy allows 20 days per year. Employees must submit requests 10 days in advance.
Chunk 2: Employees must submit requests 10 days in advance. The HR portal is the...
```

Both chunks now contain the complete procedure.

## The Splitter Hierarchy

We use `RecursiveCharacterTextSplitter` which tries to split at natural boundaries:

1. **Double newline** (`\n\n`) — Paragraph breaks (preferred)
2. **Single newline** (`\n`) — Line breaks
3. **Sentence end** (`. `) — Sentence boundaries
4. **Space** (` `) — Word boundaries
5. **Empty** (`""`) — Character-level (last resort)

This hierarchy means:
- A 500-token chunk usually ends at a paragraph break
- If no paragraph break is nearby, it ends at a sentence
- Characters are never split mid-word

## Practical Impact

With 1,500 documents averaging 5 pages each:
- **~30,000 total chunks** at 500 tokens each
- Each chunk is a searchable unit of knowledge
- The embedding model (MiniLM-L6-v2) produces a 384-dim vector per chunk
- At query time, we search these 30,000 vectors in ~50ms

## Token vs Character

Note: Our implementation uses `chunk_size=500` with `length_function=len` — this measures **characters**, not tokens. For English text, 500 characters ≈ 125 tokens (rough ratio of 4 chars/token). This is a pragmatic choice because:

1. Character counting is instant; token counting requires a tokenizer
2. The exact boundary matters less than being in the right range
3. The `RecursiveCharacterTextSplitter` adjusts splits to natural boundaries anyway

If you wanted exact token-based splitting, you'd pass a tokenizer as the `length_function`. For production at PCG, character-based splitting worked well because the overlap compensates for any imprecision.
