export default {
  async scheduled(_event, env) {
    const res = await fetch("https://api.github.com/repos/dlwr/kose-sports/actions/workflows/build.yml/dispatches", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${env.GITHUB_TOKEN}`,
        Accept: "application/vnd.github+json",
        "User-Agent": "kose-sports-trigger",
      },
      body: JSON.stringify({ ref: "main" }),
    });
    if (!res.ok) throw new Error(`dispatch failed: ${res.status} ${await res.text()}`);
  },
};
