from .config import GGUF_DIR, MERGED_DIR, SYSTEM_PROMPT


def build_messages(context, question, answer=None, system=SYSTEM_PROMPT):
    user = f"Context:\n{context.strip()}\n\nQuestion:\n{question.strip()}" if context and context.strip() else question.strip()
    msgs = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    if answer is not None:
        msgs.append({"role": "assistant", "content": answer.strip()})
    return msgs


class Generator:

    def __init__(self, backend, gguf=None, quant="Q4_K_M", max_tokens=300):
        self.backend, self.max_tokens = backend, max_tokens
        if backend == "mlx":
            from mlx_lm import load

            self.model, self.tok = load(str(MERGED_DIR))
        else:
            from llama_cpp import Llama

            path = gguf or str(GGUF_DIR / f"model-{quant}.gguf")
            self.llm = Llama(model_path=path, n_ctx=2048, n_gpu_layers=-1, verbose=False)

    def stream(self, msgs, max_tokens=None):
        mt = max_tokens or self.max_tokens
        if self.backend == "mlx":
            try:
                from mlx_lm import stream_generate
            except ImportError:
                yield self(msgs, mt)
                return

            prompt = self.tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
            for r in stream_generate(self.model, self.tok, prompt=prompt, max_tokens=mt):
                yield r if isinstance(r, str) else getattr(r, "text", None) or (r[0] if isinstance(r, tuple) else "")
        else:
            for ch in self.llm.create_chat_completion(messages=msgs, max_tokens=mt, temperature=0.1, stream=True):
                d = ch["choices"][0]["delta"].get("content")
                if d:
                    yield d

    def __call__(self, msgs, max_tokens=None):
        mt = max_tokens or self.max_tokens
        if self.backend == "mlx":
            from mlx_lm import generate

            prompt = self.tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
            return generate(self.model, self.tok, prompt=prompt, max_tokens=mt).strip()
        res = self.llm.create_chat_completion(messages=msgs, max_tokens=mt, temperature=0.1)
        return res["choices"][0]["message"]["content"].strip()


def cmd_test(args):
    gen = Generator(args.backend, args.gguf, args.quant, args.max_tokens)
    print(gen(build_messages(args.context, args.question)))
