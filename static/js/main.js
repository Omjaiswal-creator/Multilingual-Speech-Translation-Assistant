
  document.getElementById('audio-input').addEventListener('change', function () {
    document.getElementById('file-name').textContent =
      this.files.length ? this.files[0].name : 'Choose audio file';
  });

  document.getElementById('swap-btn').addEventListener('click', function () {
    const src = document.getElementById('source_lang');
    const tgt = document.getElementById('target_lang');
    const tmp = src.value;
    src.value = tgt.value;
    tgt.value = tmp;
  });

  function copyResult() {
    const text = document.querySelector('.result-text');
    if (!text) return;
    navigator.clipboard.writeText(text.innerText).then(() => {
      const lbl = document.getElementById('copy-label');
      lbl.textContent = 'Copied!';
      setTimeout(() => lbl.textContent = 'Copy', 2000);
    });
  }
