function uploadPanel(parent) {
  return {
    uploading: false,
    lastResult: null,
    async upload(milestoneId, fileEl) {
      const file = fileEl.files[0];
      if (!file) return;
      this.uploading = true;
      const fd = new FormData();
      fd.append('file', file);
      try {
        const r = await fetch(`/api/validate/${milestoneId}`, {method: 'POST', body: fd});
        this.lastResult = await r.json();
        await parent.refresh();
      } finally { this.uploading = false; }
    }
  }
}
