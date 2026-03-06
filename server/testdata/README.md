# testdata

- `test_ja_1s.wav` は 440Hz 正弦波で、音声フォーマット確認用。ASR の PASS 判定には使わない。
- `test_en_hello_16k.wav` は spoken WAV の疎通確認用。`/v1/realtime` の smoke test ではこちらを使う。
- `generate_test_wav.py` は `test_ja_1s.wav` を生成する。
