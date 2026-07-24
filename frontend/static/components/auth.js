function authView(parent) {
  return {
    mode: 'login',
    form: { username: '', password: '', display_name: '' },
    error: null,
    loading: false,

    async submit() {
      this.loading = true;
      this.error = null;
      try {
        const url = this.mode === 'login' ? '/api/auth/login' : '/api/auth/register';
        const body = this.mode === 'login'
          ? { username: this.form.username, password: this.form.password }
          : this.form;
        const r = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });
        if (!r.ok) {
          const e = await r.json();
          throw new Error(e.detail || '操作失败');
        }
        const data = await r.json();
        parent.setToken(data.token);
        await parent.fetchUser();
        parent.navigate('projects');
      } catch (e) {
        this.error = e.message;
      } finally {
        this.loading = false;
      }
    }
  }
}
