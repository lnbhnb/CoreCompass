function notifyLog(parent) {
  return {
    logs: [],
    async load() {
      const r = await fetch('/api/notifications?limit=20');
      this.logs = await r.json();
    },
    async testPush() {
      await fetch(`/api/notify/test?project_id=${parent.project?.id || ''}`, {method: 'POST'});
      await this.load();
    },
    init() { this.load(); }
  }
}
