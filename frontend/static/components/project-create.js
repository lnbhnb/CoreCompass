function projectCreate(parent) {
  return {
    form: {name: '', deadline: '', team_size: 3, topic_desc: ''},
    submitting: false,
    async submit() {
      this.submitting = true;
      try { await parent.createProject(this.form); }
      finally { this.submitting = false; }
    }
  }
}
