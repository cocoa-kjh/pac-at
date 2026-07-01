export default function Settings() {
  return (
    <div>
      <h2>설정</h2>
      <div className="card">
        <h3>YouTube 연동</h3>
        <p style={{ color: "var(--text-dim)", marginBottom: 16, fontSize: 13 }}>
          OAuth 인증이 필요합니다. 아래 버튼으로 Google 계정을 연결하세요.
        </p>
        <a
          href="http://localhost:8000/auth/youtube"
          className="btn-primary"
          style={{
            display: "inline-block",
            padding: "8px 16px",
            borderRadius: 4,
            background: "var(--accent)",
            color: "#fff",
            fontWeight: 500,
            textDecoration: "none",
          }}
        >
          YouTube 연결 / 재인증
        </a>
      </div>
    </div>
  );
}
