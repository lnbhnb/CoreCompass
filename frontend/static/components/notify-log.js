function notifyLog(parent) {
  return {
    logs: [],
    async load() {
      const r = await fetch('/api/notifications?limit=20', { headers: parent.authHeaders() });
      this.logs = await r.json();
    },
    async testPush() {
      await fetch(`/api/notify/test?project_id=${parent.project?.id || ''}`, { method: 'POST', headers: parent.authHeaders() });
      await this.load();
    },
    typeMeta(type) {
      return {
        task_submit: { label: '提交', cls: 'nt-submit' },
        task_review: { label: '审阅', cls: 'nt-review' },
        overdue: { label: '逾期', cls: 'nt-overdue' },
        replan: { label: '重规划', cls: 'nt-replan' },
        milestone: { label: '里程碑', cls: 'nt-milestone' }
      }[type] || { label: type || '通知', cls: '' };
    },
    init() { this.load(); }
  }
}
