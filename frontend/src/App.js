import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { BrowserRouter, Link, Navigate, Route, Routes, useLocation, useNavigate, useParams } from "react-router-dom";
import axios from "axios";
import "@/App.css";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/* ---------- helpers ---------- */
const blankMember = (number) => ({ member_number: number, name: "", registration_number: "", email: "", phone: "", gender: "", year: "", branch: "", section: "", euphoria_id: "", accommodation_type: "day_scholar", hostel: null });
const emptyDraft = { team_name: "", college_type: "internal", college_name: "", members: [1, 2, 3, 4].map(blankMember), confirmation_accepted: false };
const GENDERS = ["Male", "Female", "Prefer not to say"];
const YEARS = ["I", "II", "III", "IV", "V"];
const BRANCHES = ["CSE", "ECE", "IT", "EEE", "MECH", "CIVIL", "AIDS", "AIML", "Other"];

const FACULTY_COORDINATORS = [
  { name: "Mrs. N. Kirthiga", role: "AP/CSE" },
  { name: "Mrs. S. Reshni", role: "AP/CSE" },
  { name: "Mrs. B. Lavanya", role: "AP/CSE" },
  { name: "Mrs. S. Shanmuga Priya", role: "AP/CSE" },
  { name: "Mr. C. Sivamurugan", role: "AP/CSE" },
  { name: "Dr. M. K. Nagarajan", role: "AP/CSE" },
  { name: "Dr. R. Raja Sekar", role: "AP/CSE" },
  { name: "Dr. T. Dhilipan Rajkumar", role: "AP/CSE" },
  { name: "Mrs. P. J. Kruthika", role: "AP/CSE" },
  { name: "Mr. Aravind Chandran", role: "AP/CSE" },
];
const FACULTY_SPONSOR = { name: "Dr. P. Chinnasamy", role: "ACM / IEEE EDU SBC Counsellor · KARE · ASP/CSE" };
const REGISTRAR = { name: "Dr. V. Vasudevan", role: "Registrar" };
const STUDENT_COORDINATORS = [
  { name: "L. Harsha Vardhan", role: "Student Coordinator", phone: "+91 91005 50609", phoneRaw: "+919100550609" },
  { name: "P. Harshika Suryanjali", role: "Student Coordinator", phone: "+91 95027 95304", phoneRaw: "+919502795304" },
  { name: "S. Thaha", role: "Student Coordinator", phone: "+91 78933 40788", phoneRaw: "+917893340788" },
  { name: "G. Umesh Chandra", role: "Student Coordinator", phone: "+91 95738 61418", phoneRaw: "+919573861418" },
];
const FACULTY_CONTACTS = [
  { name: "Dr. P. Chinnasamy", phone: "+91 96002 81664", phoneRaw: "+919600281664" },
  { name: "Dr. R. Raja Sekar", phone: "+91 63821 72610", phoneRaw: "+916382172610" },
];

const buildDraft = (data) => ({ ...emptyDraft, ...data });

const mediaUrl = (path) => path ? (path.startsWith("http") ? path : `${API}/media/${path}`) : null;

const formatEventDates = (startsAt, endsAt) => {
  if (!startsAt) return null;
  try {
    const s = new Date(startsAt);
    const e = endsAt ? new Date(endsAt) : null;
    const opts = { day: "numeric", month: "short", year: "numeric" };
    const timeOpts = { hour: "2-digit", minute: "2-digit" };
    const startStr = s.toLocaleDateString("en-IN", opts);
    if (e && (s.toDateString() !== e.toDateString())) {
      return `${s.toLocaleDateString("en-IN", { day: "numeric", month: "short" })} – ${e.toLocaleDateString("en-IN", opts)} · ${s.toLocaleTimeString("en-IN", timeOpts)} start`;
    }
    return `${startStr} · ${s.toLocaleTimeString("en-IN", timeOpts)}`;
  } catch { return null; }
};

function Countdown({ target, label = "Kick-off in" }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    if (!target) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [target]);
  if (!target) return null;
  const diff = Math.max(0, new Date(target).getTime() - now);
  const seconds = Math.floor(diff / 1000);
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  const pad = (n) => String(n).padStart(2, "0");
  const done = diff === 0;
  return (
    <div className={`countdown ${done ? "countdown-live" : ""}`} data-testid="countdown">
      <span className="countdown-label">{done ? "The Hackathon has started" : label}</span>
      <div className="countdown-units">
        <div className="countdown-unit"><strong data-testid="countdown-days">{pad(days)}</strong><span>Days</span></div>
        <div className="countdown-unit"><strong data-testid="countdown-hours">{pad(hours)}</strong><span>Hours</span></div>
        <div className="countdown-unit"><strong data-testid="countdown-minutes">{pad(mins)}</strong><span>Minutes</span></div>
        <div className="countdown-unit"><strong data-testid="countdown-seconds">{pad(secs)}</strong><span>Seconds</span></div>
      </div>
    </div>
  );
}

/* ---------- Intro ---------- */
function Intro({ clubs, onSkip }) {
  const [visible, setVisible] = useState(true);
  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const timeout = setTimeout(() => { setVisible(false); onSkip?.(); }, reduced ? 400 : 4200);
    return () => clearTimeout(timeout);
  }, [onSkip]);
  if (!visible) return null;
  const skip = () => { setVisible(false); onSkip?.(); };
  return (
    <div className="intro" data-testid="intro-overlay" role="dialog" aria-label="Euphoria collaboration introduction">
      <div className="intro-grid" />
      <div className="intro-orbit orbit-one" />
      <div className="intro-orbit orbit-two" />
      <p className="eyebrow">A collaboration of five communities</p>
      <h1 data-testid="intro-title">EUPHORIA</h1>
      <p className="intro-subtitle">ONE HACKATHON · ONE FUTURE</p>
      <div className="intro-logos">
        {(clubs || []).slice(0, 5).map((club, idx) => (
          <div key={club.slug || idx} className="intro-logo-badge" aria-label={club.name}>
            {club.logoUrl ? <img src={mediaUrl(club.logoUrl)} alt={club.name} /> : <span>{idx + 1}</span>}
          </div>
        ))}
        {(!clubs || clubs.length === 0) && Array.from({ length: 5 }).map((_, i) => <div key={i} className="intro-logo-badge"><span>{i + 1}</span></div>)}
      </div>
      <button className="text-button" onClick={skip} data-testid="skip-intro-button">Skip intro <span>↗</span></button>
    </div>
  );
}

/* ---------- Landing ---------- */
function Landing() {
  const navigate = useNavigate();
  const [intro, setIntro] = useState(true);
  const [hackathon, setHackathon] = useState(null);
  const [clubs, setClubs] = useState([]);
  const [openRule, setOpenRule] = useState(0);

  useEffect(() => {
    let alive = true;
    Promise.all([axios.get(`${API}/hackathon`).catch(() => null), axios.get(`${API}/clubs`).catch(() => null)]).then(([h, c]) => {
      if (!alive) return;
      setHackathon(h?.data?.data || null);
      setClubs(c?.data?.data || []);
    });
    return () => { alive = false; };
  }, []);

  const hackathonName = hackathon?.name || "Hack Odyssey 4.0";
  const tagline = hackathon?.tagline || "A 24-hour hackathon inside Euphoria 2026.";
  const rules = hackathon?.rules || [];
  const eligibility = hackathon?.eligibility || [];
  const instructions = hackathon?.instructions || [];
  const sdgs = hackathon?.sdgGoals || [];
  const eventDates = formatEventDates(hackathon?.startsAt, hackathon?.endsAt);
  const clubList = clubs.length ? clubs : Array.from({ length: 5 }).map((_, i) => ({ name: `[CLUB_0${i + 1}]`, slug: `club-0${i + 1}`, displayOrder: i + 1 }));

  return (
    <main className="site-shell">
      {intro && <Intro clubs={clubList} onSkip={() => setIntro(false)} />}
      <nav className="nav" data-testid="landing-navigation">
        <Link to="/" className="brand" data-testid="brand-link"><span>EU</span>PHORIA</Link>
        <div className="nav-links">
          <a href="#collaboration" data-testid="nav-collaboration-link">Collaboration</a>
          <a href="#rules" data-testid="nav-rules-link">Rules</a>
          <a href="#coordinators" data-testid="nav-coordinators-link">Coordinators</a>
          <a href="#sdgs" data-testid="nav-sdgs-link">SDG Goals</a>
          <Link to="/register" className="nav-cta" data-testid="nav-register-link">Register now ↗</Link>
        </div>
      </nav>

      <section className="hero" data-testid="landing-hero">
        <div className="hero-copy">
          <p className="eyebrow" data-testid="hero-eyebrow">Euphoria 2026 · Team Registration</p>
          <h1 data-testid="hero-title">{hackathonName}<br /><em>the future.</em></h1>
          <p className="hero-text" data-testid="hero-tagline">{tagline}</p>
          {(eventDates || hackathon?.venue || hackathon?.mode || hackathon?.fee || hackathon?.prizePool) && (
            <ul className="event-chips" data-testid="event-chips">
              {eventDates && <li data-testid="chip-dates"><span>Dates</span><b>{eventDates}</b></li>}
              {hackathon?.venue && <li data-testid="chip-venue"><span>Venue</span><b>{hackathon.venue}</b></li>}
              {hackathon?.mode && <li data-testid="chip-mode"><span>Mode</span><b>{hackathon.mode}</b></li>}
              {hackathon?.fee && <li data-testid="chip-fee"><span>Fee</span><b>{hackathon.fee}</b></li>}
              {hackathon?.prizePool && <li data-testid="chip-prize"><span>Prize</span><b>{hackathon.prizePool}</b></li>}
              {hackathon?.sponsoredBy && <li data-testid="chip-sponsor"><span>Sponsor</span><b>{hackathon.sponsoredBy}</b></li>}
            </ul>
          )}
          <Countdown target={hackathon?.startsAt} />
          <button className="gold-button" onClick={() => navigate("/register")} data-testid="hero-register-button">Register your team <span>↗</span></button>
        </div>
        <div className="hero-mark" aria-hidden="true">
          <div className="mark-ring ring-a" />
          <div className="mark-ring ring-b" />
          <div className="mark-core">EU<br /><small>26</small></div>
        </div>
        <div className="scroll-hint">Scroll to explore <span>↓</span></div>
      </section>

      <section id="collaboration" className="section collaboration-section">
        <div className="section-head">
          <p className="eyebrow">Five communities · one direction</p>
          <h2>Built together.</h2>
          <p>These clubs are collaborators, not categories. Every team registers once for the one Euphoria Hackathon.</p>
        </div>
        <div className="club-grid" data-testid="club-grid">
          {clubList.map((club, index) => (
            <article className="club-card" key={club.slug || index} data-testid={`club-card-${index + 1}`}>
              <div className="club-number">0{index + 1}</div>
              <div className="club-logo">{club.logoUrl ? <img src={mediaUrl(club.logoUrl)} alt={club.name} /> : <div className="club-placeholder">{club.name.replace(/[^A-Z0-9]/g, "").slice(0, 2) || `C${index + 1}`}</div>}</div>
              <h3>{club.name}</h3>
              {(club.facultyInCharge || club.studentInCharge) && (
                <p className="club-meta">
                  {club.facultyInCharge && <span>Faculty · {club.facultyInCharge}</span>}
                  {club.studentInCharge && <span>Student · {club.studentInCharge}</span>}
                </p>
              )}
              <span className="club-arrow">↗</span>
            </article>
          ))}
        </div>
      </section>

      <section id="rules" className="section rules-section">
        <div className="section-head">
          <p className="eyebrow">Read before you build</p>
          <h2>Rules & instructions.</h2>
          <p>Read every clause carefully. Placeholders remain until organizers publish the official rules.</p>
        </div>
        <div className="accordion-grid">
          <div>
            <p className="accordion-label">Rules & Regulations</p>
            {rules.length ? rules.map((r, i) => (
              <div key={i} className={`accordion ${openRule === i ? "open" : ""}`} data-testid={`rule-${i}`}>
                <button onClick={() => setOpenRule(openRule === i ? -1 : i)}><span>0{i + 1}</span>{r.title}<i>{openRule === i ? "−" : "+"}</i></button>
                {openRule === i && <p>{r.body}</p>}
              </div>
            )) : <p className="muted">Rules will appear once organizers publish them.</p>}
          </div>
          <div>
            <p className="accordion-label">Eligibility</p>
            {eligibility.map((r, i) => <div key={i} className="accordion open" data-testid={`eligibility-${i}`}><strong>{r.title}</strong><p>{r.body}</p></div>)}
          </div>
          <div>
            <p className="accordion-label">Important Instructions</p>
            {instructions.map((r, i) => <div key={i} className="accordion open" data-testid={`instruction-${i}`}><strong>{r.title}</strong><p>{r.body}</p></div>)}
          </div>
        </div>
      </section>

      <section id="coordinators" className="section coordinators-section">
        <div className="section-head">
          <p className="eyebrow">Talk to the team</p>
          <h2>Coordinators.</h2>
          <p>Reach out to the student coordinators for any registration or logistics questions. Faculty coordinators and the sponsor oversee the event.</p>
        </div>
        <div className="coord-grid">
          <div className="coord-column">
            <p className="accordion-label">Student coordinators</p>
            <div className="student-coord-list">
              {STUDENT_COORDINATORS.map((s) => (
                <a key={s.phoneRaw} href={`tel:${s.phoneRaw}`} className="student-coord-card" data-testid={`student-coord-${s.phoneRaw}`}>
                  <div className="coord-avatar">{s.name.split(" ").map((p) => p[0]).slice(0, 2).join("")}</div>
                  <div>
                    <strong>{s.name}</strong>
                    <span>{s.phone}</span>
                  </div>
                  <i>↗</i>
                </a>
              ))}
            </div>
            <p className="accordion-label" style={{ marginTop: 36 }}>Faculty contact</p>
            <div className="student-coord-list">
              {FACULTY_CONTACTS.map((f) => (
                <a key={f.phoneRaw} href={`tel:${f.phoneRaw}`} className="student-coord-card faculty-contact-card" data-testid={`faculty-contact-${f.phoneRaw}`}>
                  <div className="coord-avatar">{f.name.split(" ").map((p) => p[0]).slice(0, 2).join("")}</div>
                  <div>
                    <strong>{f.name}</strong>
                    <span>{f.phone}</span>
                  </div>
                  <i>↗</i>
                </a>
              ))}
            </div>
            <p className="accordion-label" style={{ marginTop: 36 }}>Faculty sponsor & registrar</p>
            <div className="sponsor-card" data-testid="faculty-sponsor">
              <strong>{FACULTY_SPONSOR.name}</strong>
              <span>{FACULTY_SPONSOR.role}</span>
            </div>
            <div className="sponsor-card" data-testid="registrar">
              <strong>{REGISTRAR.name}</strong>
              <span>{REGISTRAR.role}</span>
            </div>
          </div>
          <div className="coord-column">
            <p className="accordion-label">Faculty coordinators · {FACULTY_COORDINATORS.length}</p>
            <div className="faculty-grid">
              {FACULTY_COORDINATORS.map((f, i) => (
                <div key={f.name} className="faculty-card" data-testid={`faculty-coord-${i + 1}`}>
                  <span className="mono">{String(i + 1).padStart(2, "0")}</span>
                  <div>
                    <strong>{f.name}</strong>
                    <span>{f.role}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section id="sdgs" className="section sdg-section">
        <div className="section-head">
          <p className="eyebrow">The challenge field</p>
          <h2>Build with purpose.</h2>
          <p>Explore problems that demand technical imagination and human-centered solutions.</p>
        </div>
        <div className="sdg-grid">
          {sdgs.map((goal, index) => (
            <div className="sdg-row" key={goal.code || index} data-testid={`sdg-goal-${index + 1}`}>
              <span>{goal.code}</span>
              <strong>{goal.title}</strong>
              <i>↗</i>
            </div>
          ))}
        </div>
      </section>

      <section className="final-cta">
        <p className="eyebrow">Your next chapter starts here</p>
        <h2>Bring the team.<br /><em>Make it real.</em></h2>
        <button className="gold-button" onClick={() => navigate("/register")} data-testid="final-register-button">Start registration <span>↗</span></button>
      </section>

      <footer className="footer">
        <span>© EUPHORIA HACKATHON</span>
        <span>Development preview · Official details pending</span>
        <Link to="/admin/login" data-testid="admin-link">Organizer sign-in ↗</Link>
      </footer>
      <a className="built-by-badge" href="#collaboration" data-testid="built-by-badge">
        <span className="built-by-dot" />
        <span>Built by <b>GFG Campus Body · KARE</b></span>
      </a>
    </main>
  );
}

/* ---------- Form fields ---------- */
function Field({ label, value, onChange, type = "text", required = true, placeholder = "", testId }) {
  return (
    <label className="field">
      <span>{label}{required && <b>*</b>}</span>
      <input value={value} onChange={onChange} type={type} required={required} placeholder={placeholder} data-testid={testId} />
    </label>
  );
}

function SelectField({ label, value, onChange, options, testId, required = true }) {
  return (
    <label className="field">
      <span>{label}{required && <b>*</b>}</span>
      <select value={value} onChange={onChange} data-testid={testId} required={required}>
        <option value="">Select…</option>
        {options.map((option) => <option key={option} value={option}>{option}</option>)}
      </select>
    </label>
  );
}

function MemberCard({ member, index, update, remove, collegeType }) {
  const set = (key, value) => update({ ...member, [key]: value });
  const prefix = `member-${member.member_number}`;
  const isLead = member.member_number === 1;
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");

  const uploadIdProof = async (file) => {
    if (!file) return;
    setUploadError("");
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await axios.post(`${API}/uploads/id-proof`, fd, { headers: { "Content-Type": "multipart/form-data" } });
      const data = res.data.data;
      update({ ...member, id_proof: { path: data.path, filename: data.filename, content_type: data.content_type } });
    } catch (e) {
      setUploadError(e.response?.data?.detail?.message || "Upload failed. Try a smaller PNG/JPG/PDF.");
    } finally {
      setUploading(false);
    }
  };

  return (
    <article className="member-card" data-testid={`member-card-${member.member_number}`}>
      <div className="member-heading">
        <div>
          <p className="eyebrow">Member {String(member.member_number).padStart(2, "0")}</p>
          <h2>{isLead ? "Team lead" : `Contributor 0${index}`}</h2>
        </div>
        {member.member_number === 5 && (
          <button className="remove-button" onClick={remove} type="button" data-testid="remove-member-five-button">Remove member 05</button>
        )}
      </div>
      <div className="field-grid">
        <Field label="Name" testId={`${prefix}-name-input`} value={member.name} onChange={(e) => set("name", e.target.value)} />
        <Field label="Registration number" testId={`${prefix}-registration-number-input`} value={member.registration_number} onChange={(e) => set("registration_number", e.target.value)} />
        <Field label="College email" testId={`${prefix}-email-input`} value={member.email} type="email" onChange={(e) => set("email", e.target.value)} />
        <Field label="Phone number" testId={`${prefix}-phone-input`} value={member.phone} type="tel" onChange={(e) => set("phone", e.target.value)} />
        <SelectField label="Gender" testId={`${prefix}-gender-select`} value={member.gender} options={GENDERS} onChange={(e) => set("gender", e.target.value)} />
        <SelectField label="Year" testId={`${prefix}-year-select`} value={member.year} options={YEARS} onChange={(e) => set("year", e.target.value)} />
        <SelectField label="Branch" testId={`${prefix}-branch-select`} value={member.branch} options={BRANCHES} onChange={(e) => set("branch", e.target.value)} />
        <Field label="Section" testId={`${prefix}-section-input`} value={member.section} onChange={(e) => set("section", e.target.value)} />
        <Field label="Euphoria ID" testId={`${prefix}-euphoria-id-input`} value={member.euphoria_id} onChange={(e) => set("euphoria_id", e.target.value)} placeholder="Issued by Euphoria registration" />
      </div>
      {collegeType === "internal" && (
        <div className="accommodation">
          <span className="field-label">Accommodation<b>*</b></span>
          <div className="radio-row">
            <label><input type="radio" checked={member.accommodation_type === "day_scholar"} onChange={() => { set("accommodation_type", "day_scholar"); update({ ...member, accommodation_type: "day_scholar", hostel: null }); }} data-testid={`${prefix}-day-scholar-radio`} /> Day Scholar</label>
            <label><input type="radio" checked={member.accommodation_type === "hosteller"} onChange={() => set("accommodation_type", "hosteller")} data-testid={`${prefix}-hosteller-radio`} /> Hosteller</label>
          </div>
          {member.accommodation_type === "hosteller" && (
            <div className="field-grid hostel-grid">
              <Field label="Hostel name" testId={`${prefix}-hostel-name-input`} value={member.hostel?.hostel_name || ""} onChange={(e) => set("hostel", { ...(member.hostel || {}), hostel_name: e.target.value })} />
              <Field label="Room number" testId={`${prefix}-room-number-input`} value={member.hostel?.room_number || ""} onChange={(e) => set("hostel", { ...(member.hostel || {}), room_number: e.target.value })} />
              <Field label="Warden name" testId={`${prefix}-warden-name-input`} value={member.hostel?.warden_name || ""} onChange={(e) => set("hostel", { ...(member.hostel || {}), warden_name: e.target.value })} />
              <Field label="Warden phone" testId={`${prefix}-warden-phone-input`} value={member.hostel?.warden_phone || ""} onChange={(e) => set("hostel", { ...(member.hostel || {}), warden_phone: e.target.value })} />
            </div>
          )}
        </div>
      )}
      {isLead && (
        <div className="accommodation">
          <span className="field-label">Team lead ID proof<b>*</b></span>
          <p className="muted" style={{ fontSize: 12, margin: "6px 0 12px" }}>Upload a photo of your student ID card (PNG · JPG · PDF · max 5 MB). Only shared with organizers.</p>
          <label className="uploader" data-testid="id-proof-uploader">
            <input type="file" accept="image/*,application/pdf" onChange={(e) => uploadIdProof(e.target.files?.[0])} data-testid={`${prefix}-id-proof-input`} />
            <span>{uploading ? "Uploading…" : member.id_proof ? `Replace file (${member.id_proof.filename})` : "Choose file to upload"}</span>
          </label>
          {member.id_proof && !uploading && <p className="upload-ok" data-testid="id-proof-ok">✓ {member.id_proof.filename} attached</p>}
          {uploadError && <p className="upload-error" data-testid="id-proof-error">{uploadError}</p>}
        </div>
      )}
    </article>
  );
}

/* ---------- Registration ---------- */
function Registration({ draft, setDraft }) {
  const navigate = useNavigate();
  const submit = () => navigate("/register/review");
  const updateMember = (index, value) => setDraft({ ...draft, members: draft.members.map((m, i) => i === index ? value : m) });
  const setCollegeType = (value) => {
    let members = draft.members;
    if (value === "external") {
      members = members.map((m) => ({ ...m, accommodation_type: null, hostel: null }));
    } else {
      members = members.map((m) => ({ ...m, accommodation_type: m.accommodation_type || "day_scholar" }));
    }
    setDraft({ ...draft, college_type: value, members, college_name: value === "external" ? draft.college_name : "" });
  };

  return (
    <main className="form-shell">
      <nav className="nav form-nav">
        <Link to="/" className="brand" data-testid="form-brand-link"><span>EU</span>PHORIA</Link>
        <Link to="/" className="back-link" data-testid="form-back-link">← Back to overview</Link>
      </nav>
      <div className="progress" data-testid="progress-indicator">
        <span className="active">01 <b>Details</b></span><i />
        <span>02 <b>Review</b></span><i />
        <span>03 <b>Success</b></span>
      </div>
      <section className="form-intro">
        <p className="eyebrow">Centralized team registration</p>
        <h1>Bring your best team.</h1>
        <p>Four members are required. A fifth teammate can be added when your idea needs one more perspective.</p>
      </section>
      <form onSubmit={(e) => { e.preventDefault(); submit(); }}>
        <section className="team-card">
          <div className="member-heading">
            <div><p className="eyebrow">Team details</p><h2>Set your direction.</h2></div>
            <span className="required-note">* Required</span>
          </div>
          <div className="field-grid">
            <Field label="Team name" testId="team-name-input" value={draft.team_name} onChange={(e) => setDraft({ ...draft, team_name: e.target.value })} />
            <label className="field">
              <span>College type<b>*</b></span>
              <select value={draft.college_type} onChange={(e) => setCollegeType(e.target.value)} data-testid="college-type-select">
                <option value="internal">Internal College</option>
                <option value="external">External College</option>
              </select>
            </label>
            {draft.college_type === "external" && (
              <Field label="College name" testId="college-name-input" value={draft.college_name} onChange={(e) => setDraft({ ...draft, college_name: e.target.value })} />
            )}
          </div>
        </section>
        {draft.members.map((member, index) => (
          <MemberCard key={member.member_number} member={member} index={index} collegeType={draft.college_type} update={(value) => updateMember(index, value)} remove={() => setDraft({ ...draft, members: draft.members.slice(0, 4) })} />
        ))}
        {draft.members.length === 4 && (
          <button className="add-member" type="button" onClick={() => setDraft({ ...draft, members: [...draft.members, blankMember(5)] })} data-testid="add-member-five-button">+ Add optional member 05</button>
        )}
        <button className="gold-button wide" type="submit" data-testid="continue-review-button">Continue to review <span>↗</span></button>
      </form>
    </main>
  );
}

/* ---------- Review ---------- */
function Review({ draft, setDraft }) {
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const inFlight = useRef(false);

  const submit = async () => {
    if (inFlight.current) return;
    setError("");
    setLoading(true);
    inFlight.current = true;
    try {
      const response = await axios.post(`${API}/registrations`, draft);
      const data = response.data.data;
      navigate(`/register/success/${data.registration_id}`, { state: data });
    } catch (e) {
      const detail = e.response?.data?.detail;
      setError(typeof detail === "string" ? detail : detail?.message || "Please review the highlighted information and try again.");
    } finally {
      setLoading(false);
      inFlight.current = false;
    }
  };

  return (
    <main className="form-shell">
      <nav className="nav form-nav">
        <Link to="/" className="brand" data-testid="review-brand-link"><span>EU</span>PHORIA</Link>
        <Link to="/register" className="back-link" data-testid="review-back-link">← Edit details</Link>
      </nav>
      <div className="progress" data-testid="progress-indicator">
        <span className="done">01 <b>Details</b></span><i />
        <span className="active">02 <b>Review</b></span><i />
        <span>03 <b>Success</b></span>
      </div>
      <section className="form-intro">
        <p className="eyebrow">Final review</p>
        <h1>Check every detail.</h1>
        <p>Once submitted, your registration cannot be edited publicly.</p>
      </section>
      {error && <div className="form-error" role="alert" data-testid="registration-error">{error}</div>}
      <section className="review">
        <div className="review-summary">
          <div><span>Team name</span><strong data-testid="review-team-name">{draft.team_name || "—"}</strong></div>
          <div><span>College type</span><strong data-testid="review-college-type">{draft.college_type}</strong></div>
          {draft.college_name && <div><span>College</span><strong data-testid="review-college-name">{draft.college_name}</strong></div>}
        </div>
        {draft.members.map((m) => (
          <article className="review-member" key={m.member_number} data-testid={`review-member-${m.member_number}`}>
            <div><span>Member {m.member_number}{m.member_number === 1 ? " · Team lead" : ""}</span><strong>{m.name || "Unnamed member"}</strong></div>
            <div><span>Registration</span><strong>{m.registration_number || "—"}</strong></div>
            <div><span>Email</span><strong>{m.email || "—"}</strong></div>
            <div><span>Phone</span><strong>{m.phone || "—"}</strong></div>
            <div><span>Year · Branch · Section</span><strong>{[m.year, m.branch, m.section].filter(Boolean).join(" · ") || "—"}</strong></div>
            <div><span>Gender</span><strong>{m.gender || "—"}</strong></div>
            <div><span>Euphoria ID</span><strong>{m.euphoria_id || "—"}</strong></div>
            {m.accommodation_type && <div><span>Accommodation</span><strong>{m.accommodation_type === "hosteller" ? "Hosteller" : "Day Scholar"}</strong></div>}
            {m.accommodation_type === "hosteller" && m.hostel && (
              <div><span>Hostel</span><strong>{m.hostel.hostel_name} · Room {m.hostel.room_number} · Warden {m.hostel.warden_name} ({m.hostel.warden_phone})</strong></div>
            )}
          </article>
        ))}
        <div className="warning">
          <strong>Final verification</strong>
          <p>Please verify all the information carefully before submitting. Once the registration is submitted, the details cannot be modified.</p>
          <label>
            <input type="checkbox" checked={draft.confirmation_accepted} onChange={(e) => setDraft({ ...draft, confirmation_accepted: e.target.checked })} data-testid="confirmation-checkbox" />
            I have verified the above information and confirm that all details are correct.
          </label>
        </div>
        <div className="review-actions">
          <button className="outline-button" onClick={() => navigate("/register")} data-testid="edit-details-button">Edit details</button>
          <button className="gold-button" disabled={!draft.confirmation_accepted || loading} onClick={submit} data-testid="confirm-submit-button">{loading ? "Submitting…" : "Confirm & submit ↗"}</button>
        </div>
      </section>
    </main>
  );
}

/* ---------- Success ---------- */
function Success() {
  const location = useLocation();
  const { registrationId } = useParams();
  const [data, setData] = useState(location.state || null);
  const [loading, setLoading] = useState(!location.state);
  useEffect(() => {
    if (location.state || !registrationId) return;
    axios.get(`${API}/registrations/${registrationId}`).then((res) => setData(res.data.data)).catch(() => setData(null)).finally(() => setLoading(false));
  }, [registrationId, location.state]);
  if (loading) return <main className="success-shell"><p className="eyebrow">Loading…</p></main>;
  if (!data) return <main className="success-shell"><h1>Registration not found</h1><Link to="/" className="back-link" data-testid="success-home-link">Return to overview</Link></main>;
  return (
    <main className="success-shell">
      <div className="success-mark">✓</div>
      <p className="eyebrow">Registration received</p>
      <h1>You're on the list.</h1>
      <p className="success-copy">Your team has been successfully registered for the Euphoria Hackathon.</p>
      <div className="success-data" data-testid="success-summary">
        <div><span>Registration ID</span><strong data-testid="success-registration-id">{data.registration_id}</strong></div>
        <div><span>Team</span><strong data-testid="success-team-name">{data.team_name}</strong></div>
        <div><span>Members</span><strong data-testid="success-member-count">{data.member_count}</strong></div>
      </div>
      <div className="whatsapp-cta">
        <p className="eyebrow">Stay in the loop</p>
        <p className="success-copy">Join the WhatsApp group to receive important announcements, schedules, instructions and event updates.</p>
        <a className="gold-button" href={data.whatsapp_url || "#"} target="_blank" rel="noreferrer" data-testid="whatsapp-cta-button">Join official WhatsApp group <span>↗</span></a>
      </div>
      <Link to="/" className="back-link" data-testid="success-home-link">Return to overview</Link>
    </main>
  );
}

/* ---------- Admin ---------- */
const TOKEN_KEY = "euphoria_admin_token";
const getToken = () => localStorage.getItem(TOKEN_KEY);
const setToken = (t) => t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY);
const authHeaders = () => ({ Authorization: `Bearer ${getToken()}` });

function AdminLogin() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await axios.post(`${API}/admin/auth/login`, { email, password });
      setToken(res.data.access_token);
      navigate("/admin");
    } catch (err) {
      setError(err.response?.data?.detail?.message || "Invalid email or password");
    } finally {
      setLoading(false);
    }
  };
  return (
    <main className="admin-shell">
      <div className="admin-login">
        <p className="eyebrow">Organizer console</p>
        <h1>Sign in.</h1>
        <p className="muted">Access is limited to Euphoria organizers.</p>
        <form onSubmit={submit}>
          <Field label="Email" testId="admin-email-input" value={email} onChange={(e) => setEmail(e.target.value)} type="email" />
          <Field label="Password" testId="admin-password-input" value={password} onChange={(e) => setPassword(e.target.value)} type="password" />
          {error && <div className="form-error" role="alert" data-testid="admin-login-error">{error}</div>}
          <button className="gold-button wide" type="submit" disabled={loading} data-testid="admin-login-submit">{loading ? "Signing in…" : "Sign in ↗"}</button>
        </form>
        <Link to="/" className="back-link" data-testid="admin-back-link">← Back to landing</Link>
      </div>
    </main>
  );
}

function AdminBranding({ onError }) {
  const [hackathon, setHackathon] = useState(null);
  const [clubs, setClubs] = useState([]);
  const [busy, setBusy] = useState({});

  const load = useCallback(async () => {
    try {
      const [h, c] = await Promise.all([axios.get(`${API}/hackathon`), axios.get(`${API}/clubs`)]);
      setHackathon(h.data.data);
      setClubs(c.data.data);
    } catch { onError?.("Unable to load branding."); }
  }, [onError]);

  useEffect(() => { load(); }, [load]);

  const uploadHackathon = async (file) => {
    if (!file) return;
    setBusy((b) => ({ ...b, hack: true }));
    try {
      const fd = new FormData();
      fd.append("file", file);
      await axios.post(`${API}/admin/branding/hackathon-logo`, fd, { headers: { ...authHeaders(), "Content-Type": "multipart/form-data" } });
      await load();
    } catch (e) { onError?.(e.response?.data?.detail?.message || "Upload failed."); }
    finally { setBusy((b) => ({ ...b, hack: false })); }
  };

  const uploadClub = async (slug, file) => {
    if (!file) return;
    setBusy((b) => ({ ...b, [slug]: true }));
    try {
      const fd = new FormData();
      fd.append("file", file);
      await axios.post(`${API}/admin/branding/club-logo/${slug}`, fd, { headers: { ...authHeaders(), "Content-Type": "multipart/form-data" } });
      await load();
    } catch (e) { onError?.(e.response?.data?.detail?.message || "Upload failed."); }
    finally { setBusy((b) => ({ ...b, [slug]: false })); }
  };

  const renameClub = async (slug, name, faculty, student) => {
    const fd = new FormData();
    fd.append("name", name);
    fd.append("faculty_in_charge", faculty || "");
    fd.append("student_in_charge", student || "");
    try {
      await axios.post(`${API}/admin/branding/club/${slug}`, fd, { headers: { ...authHeaders(), "Content-Type": "multipart/form-data" } });
      await load();
    } catch (e) { onError?.(e.response?.data?.detail?.message || "Update failed."); }
  };

  return (
    <div className="branding-panel" data-testid="admin-branding">
      <div className="branding-hackathon">
        <p className="eyebrow">Hackathon logo</p>
        <div className="branding-row">
          <div className="branding-preview">
            {hackathon?.logoUrl ? <img src={mediaUrl(hackathon.logoUrl)} alt="Hackathon logo" data-testid="hackathon-logo-preview" /> : <span className="muted">No logo uploaded</span>}
          </div>
          <label className="uploader" data-testid="hackathon-logo-uploader">
            <input type="file" accept="image/*" onChange={(e) => uploadHackathon(e.target.files?.[0])} />
            <span>{busy.hack ? "Uploading…" : hackathon?.logoUrl ? "Replace logo" : "Upload hackathon logo"}</span>
          </label>
        </div>
      </div>
      <div className="branding-clubs">
        <p className="eyebrow">Collaborating clubs · 5 total</p>
        {clubs.map((club) => (
          <ClubBrandingRow key={club.slug} club={club} busy={busy[club.slug]} onUpload={(f) => uploadClub(club.slug, f)} onRename={(name, faculty, student) => renameClub(club.slug, name, faculty, student)} />
        ))}
      </div>
    </div>
  );
}

function ClubBrandingRow({ club, busy, onUpload, onRename }) {
  const [name, setName] = useState(club.name);
  const [faculty, setFaculty] = useState(club.facultyInCharge || "");
  const [student, setStudent] = useState(club.studentInCharge || "");
  useEffect(() => { setName(club.name); setFaculty(club.facultyInCharge || ""); setStudent(club.studentInCharge || ""); }, [club]);
  return (
    <div className="branding-row" data-testid={`club-branding-${club.slug}`}>
      <div className="branding-preview">
        {club.logoUrl ? <img src={mediaUrl(club.logoUrl)} alt={club.name} /> : <span className="muted">No logo</span>}
      </div>
      <div className="branding-controls">
        <div className="field-grid" style={{ gridTemplateColumns: "1fr 1fr 1fr" }}>
          <label className="field"><span>Club name</span><input value={name} onChange={(e) => setName(e.target.value)} data-testid={`club-name-${club.slug}`} /></label>
          <label className="field"><span>Faculty in charge</span><input value={faculty} onChange={(e) => setFaculty(e.target.value)} data-testid={`club-faculty-${club.slug}`} /></label>
          <label className="field"><span>Student in charge</span><input value={student} onChange={(e) => setStudent(e.target.value)} data-testid={`club-student-${club.slug}`} /></label>
        </div>
        <div className="branding-actions">
          <label className="uploader" data-testid={`club-logo-uploader-${club.slug}`}>
            <input type="file" accept="image/*" onChange={(e) => onUpload(e.target.files?.[0])} />
            <span>{busy ? "Uploading…" : club.logoUrl ? "Replace logo" : "Upload logo"}</span>
          </label>
          <button className="outline-button" onClick={() => onRename(name, faculty, student)} data-testid={`save-club-${club.slug}`}>Save details</button>
        </div>
      </div>
    </div>
  );
}

function IdProofLink({ path, filename }) {
  const [blobUrl, setBlobUrl] = useState(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => () => { if (blobUrl) URL.revokeObjectURL(blobUrl); }, [blobUrl]);
  const load = async () => {
    setBusy(true);
    try {
      const res = await axios.get(`${API}/admin/files/${path}`, { headers: authHeaders(), responseType: "blob" });
      setBlobUrl(URL.createObjectURL(res.data));
    } finally { setBusy(false); }
  };
  return (
    <div className="id-proof-block" data-testid="id-proof-block">
      <span className="eyebrow">ID proof</span>
      {blobUrl ? (
        <a href={blobUrl} target="_blank" rel="noreferrer" data-testid="id-proof-open">Open {filename || "file"} ↗</a>
      ) : (
        <button className="text-button" onClick={load} disabled={busy} data-testid="id-proof-load">{busy ? "Loading…" : `Load ${filename || "ID proof"} ↗`}</button>
      )}
    </div>
  );
}

function AdminDashboard() {
  const navigate = useNavigate();
  const [tab, setTab] = useState("registrations");
  const [stats, setStats] = useState(null);
  const [rows, setRows] = useState([]);
  const [pagination, setPagination] = useState({ page: 1, total: 0, pageSize: 25 });
  const [search, setSearch] = useState("");
  const [collegeFilter, setCollegeFilter] = useState("");
  const [teamSizeFilter, setTeamSizeFilter] = useState("");
  const [accommodationFilter, setAccommodationFilter] = useState("");
  const [error, setError] = useState("");
  const [detail, setDetail] = useState(null);

  const load = useCallback(async (page = 1) => {
    setError("");
    try {
      const [s, r] = await Promise.all([
        axios.get(`${API}/admin/statistics`, { headers: authHeaders() }),
        axios.get(`${API}/admin/registrations`, {
          headers: authHeaders(),
          params: { page, page_size: pagination.pageSize, search: search || undefined, college_type: collegeFilter || undefined, team_size: teamSizeFilter || undefined, accommodation: accommodationFilter || undefined },
        }),
      ]);
      setStats(s.data.data);
      setRows(r.data.data);
      setPagination(r.data.pagination);
    } catch (err) {
      if (err.response?.status === 401) { setToken(null); navigate("/admin/login"); return; }
      setError("Unable to load admin data.");
    }
  }, [search, collegeFilter, teamSizeFilter, accommodationFilter, pagination.pageSize, navigate]);

  useEffect(() => {
    if (!getToken()) { navigate("/admin/login"); return; }
    load(1);
  }, [load, navigate]);

  const exportCsv = async () => {
    try {
      const res = await axios.get(`${API}/admin/registrations/export`, { headers: authHeaders(), responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = `euphoria-registrations-${Date.now()}.csv`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch { setError("Unable to export CSV."); }
  };

  const openDetail = async (registrationId) => {
    try {
      const res = await axios.get(`${API}/admin/registrations/${registrationId}`, { headers: authHeaders() });
      setDetail(res.data.data);
    } catch { setError("Unable to load registration."); }
  };

  const logout = () => { setToken(null); navigate("/admin/login"); };

  return (
    <main className="admin-shell">
      <nav className="nav">
        <Link to="/" className="brand" data-testid="admin-brand-link"><span>EU</span>PHORIA · Organizer</Link>
        <div className="nav-links">
          <button className="text-button" onClick={exportCsv} data-testid="admin-export-csv">Export CSV <span>↓</span></button>
          <button className="text-button" onClick={logout} data-testid="admin-logout">Sign out ↗</button>
        </div>
      </nav>
      <section className="admin-body">
        <div className="section-head">
          <p className="eyebrow">Registration console</p>
          <h2>Team overview.</h2>
        </div>
        <div className="admin-tabs" data-testid="admin-tabs">
          <button className={tab === "registrations" ? "active" : ""} onClick={() => setTab("registrations")} data-testid="tab-registrations">Registrations</button>
          <button className={tab === "branding" ? "active" : ""} onClick={() => setTab("branding")} data-testid="tab-branding">Branding & clubs</button>
        </div>
        {error && <div className="form-error" data-testid="admin-error">{error}</div>}
        {tab === "branding" ? <AdminBranding onError={setError} /> : (
        <>
        {stats && (
          <div className="stats-grid" data-testid="admin-stats-grid">
            {[
              ["Total teams", stats.totalTeams, "total-teams"],
              ["Participants", stats.totalParticipants, "total-participants"],
              ["Internal teams", stats.internalTeams, "internal-teams"],
              ["External teams", stats.externalTeams, "external-teams"],
              ["4-member teams", stats.fourMemberTeams, "four-member"],
              ["5-member teams", stats.fiveMemberTeams, "five-member"],
              ["Hostellers", stats.hostellers, "hostellers"],
              ["Day scholars", stats.dayScholars, "day-scholars"],
            ].map(([label, value, key]) => (
              <div key={key} className="stat-card" data-testid={`stat-${key}`}>
                <span>{label}</span>
                <strong>{value}</strong>
              </div>
            ))}
          </div>
        )}
        <div className="admin-filters" data-testid="admin-filters">
          <input placeholder="Search team name, email, phone, Euphoria ID…" value={search} onChange={(e) => setSearch(e.target.value)} onKeyDown={(e) => e.key === "Enter" && load(1)} data-testid="admin-search-input" />
          <select value={collegeFilter} onChange={(e) => setCollegeFilter(e.target.value)} data-testid="admin-college-filter">
            <option value="">All colleges</option>
            <option value="internal">Internal</option>
            <option value="external">External</option>
          </select>
          <select value={teamSizeFilter} onChange={(e) => setTeamSizeFilter(e.target.value)} data-testid="admin-team-size-filter">
            <option value="">Any size</option>
            <option value="4">4 members</option>
            <option value="5">5 members</option>
          </select>
          <select value={accommodationFilter} onChange={(e) => setAccommodationFilter(e.target.value)} data-testid="admin-accommodation-filter">
            <option value="">Any accommodation</option>
            <option value="hosteller">Hosteller</option>
            <option value="day_scholar">Day scholar</option>
          </select>
          <button className="outline-button" onClick={() => load(1)} data-testid="admin-apply-filter">Apply</button>
        </div>
        <div className="admin-table" data-testid="admin-table">
          <div className="admin-row admin-head">
            <span>Registration</span><span>Team</span><span>College</span><span>Members</span><span>Submitted</span><span></span>
          </div>
          {rows.length === 0 && <div className="admin-row"><span className="muted" style={{ gridColumn: "1 / -1" }}>No registrations yet.</span></div>}
          {rows.map((row) => (
            <div className="admin-row" key={row.registrationId} data-testid={`admin-row-${row.registrationId}`}>
              <span className="mono">{row.registrationId}</span>
              <span>{row.teamName}</span>
              <span>{row.collegeType}{row.collegeName ? ` · ${row.collegeName}` : ""}</span>
              <span>{row.memberCount}</span>
              <span className="mono">{new Date(row.submittedAt).toLocaleString()}</span>
              <button className="text-button" onClick={() => openDetail(row.registrationId)} data-testid={`view-detail-${row.registrationId}`}>View ↗</button>
            </div>
          ))}
        </div>
        <div className="pagination">
          <button className="outline-button" disabled={pagination.page <= 1} onClick={() => load(pagination.page - 1)} data-testid="admin-prev-page">← Previous</button>
          <span className="mono">Page {pagination.page} · {pagination.total} total</span>
          <button className="outline-button" disabled={pagination.page * pagination.pageSize >= pagination.total} onClick={() => load(pagination.page + 1)} data-testid="admin-next-page">Next →</button>
        </div>
        </>
        )}
      </section>
      {detail && (
        <div className="modal" role="dialog" aria-label="Registration detail" onClick={() => setDetail(null)} data-testid="detail-modal">
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setDetail(null)} data-testid="modal-close">✕</button>
            <p className="eyebrow">{detail.registrationId}</p>
            <h2>{detail.teamName}</h2>
            <p className="muted">{detail.collegeType}{detail.collegeName ? ` · ${detail.collegeName}` : ""} · {detail.memberCount} members</p>
            <div className="detail-members">
              {detail.members.map((m) => (
                <div className="detail-member" key={m.memberNumber} data-testid={`detail-member-${m.memberNumber}`}>
                  <p className="eyebrow">Member {m.memberNumber}{m.isTeamLead ? " · Team lead" : ""}</p>
                  <strong>{m.name}</strong>
                  <p>{m.email} · {m.phone}</p>
                  <p className="muted">{m.registrationNumber} · {m.year} · {m.branch} · Sec {m.section} · Euphoria {m.euphoriaId}</p>
                  {m.accommodationType && <p className="muted">Accommodation: {m.accommodationType === "hosteller" ? `Hosteller · ${m.hostelName} Room ${m.roomNumber} · Warden ${m.wardenName} (${m.wardenPhone})` : "Day scholar"}</p>}
                  {m.idProofPath && <IdProofLink path={m.idProofPath} filename={m.idProofFilename} />}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

/* ---------- Root ---------- */
function App() {
  const [draft, setDraft] = useState(emptyDraft);
  useEffect(() => {
    try { const raw = sessionStorage.getItem("euphoria_draft"); if (raw) setDraft(buildDraft(JSON.parse(raw))); } catch { /* ignore */ }
  }, []);
  useEffect(() => { try { sessionStorage.setItem("euphoria_draft", JSON.stringify(draft)); } catch { /* ignore */ } }, [draft]);
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/register" element={<Registration draft={draft} setDraft={setDraft} />} />
        <Route path="/register/review" element={<Review draft={draft} setDraft={setDraft} />} />
        <Route path="/register/success/:registrationId" element={<Success />} />
        <Route path="/admin/login" element={<AdminLogin />} />
        <Route path="/admin" element={<AdminDashboard />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
