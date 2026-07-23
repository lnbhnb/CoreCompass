function replanModal(parent) {
  return {
    open: false,
    loading: false,
    proposal: null,
    gapDays: null,
    applying: false,
    result: null,

    async propose() {
      this.open = true;
      this.loading = true;
      this.proposal = null;
      try {
        const r = await fetch(`/api/replan/${parent.project.id}/propose`, {method: 'POST'});
        const data = await r.json();
        this.gapDays = data.gap_days;
        this.proposal = data.proposal;
      } finally { this.loading = false; }
    },

    async apply() {
      if (!this.proposal) return;
      this.applying = true;
      try {
        const r = await fetch(`/api/replan/${parent.project.id}/apply`, {
          method: 'POST', headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({proposal: this.proposal})
        });
        this.result = await r.json();
        await parent.refresh();
        this.open = false;
      } finally { this.applying = false; }
    }
  }
}
