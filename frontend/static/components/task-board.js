function taskBoard(parent) {
  return {
    groupByMilestone() {
      const map = {};
      for (const t of parent.tasks) {
        if (!map[t.milestone_id]) map[t.milestone_id] = [];
        map[t.milestone_id].push(t);
      }
      return parent.milestones.map(m => ({milestone: m, tasks: map[m.id] || []}));
    },
    statusLabel(s) {
      return {planned:'待开始',doing:'进行中',done:'已完成',overdue:'已逾期',cut:'已砍'}[s] || s;
    },
    priorityLabel(p) { return {core:'核心',optional:'可选'}[p] || p; }
  }
}
