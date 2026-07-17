import { FormEvent, useEffect, useState } from "react";

type Profile = {
  displayName: string;
  email: string;
  role: string;
};

const KEY = "texllm.profile.v1";

export function ProfilePage() {
  const [profile, setProfile] = useState<Profile>(() => {
    try {
      return (
        JSON.parse(localStorage.getItem(KEY) || "null") || {
          displayName: "Operator",
          email: "",
          role: "admin",
        }
      );
    } catch {
      return { displayName: "Operator", email: "", role: "admin" };
    }
  });
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    localStorage.setItem(KEY, JSON.stringify(profile));
  }, [profile]);

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSaved(true);
    setTimeout(() => setSaved(false), 1500);
  }

  return (
    <div>
      <h1>User profile</h1>
      <p className="lede">Local operator identity for tasks (UserID) and audit UI.</p>
      <form className="card" onSubmit={onSubmit}>
        <div className="field">
          <label htmlFor="dn">Display name</label>
          <input
            id="dn"
            value={profile.displayName}
            onChange={(e) =>
              setProfile((p) => ({ ...p, displayName: e.target.value }))
            }
          />
        </div>
        <div className="field">
          <label htmlFor="em">Email</label>
          <input
            id="em"
            type="email"
            value={profile.email}
            onChange={(e) =>
              setProfile((p) => ({ ...p, email: e.target.value }))
            }
          />
        </div>
        <div className="field">
          <label htmlFor="role">Role</label>
          <select
            id="role"
            value={profile.role}
            onChange={(e) =>
              setProfile((p) => ({ ...p, role: e.target.value }))
            }
          >
            <option value="admin">admin</option>
            <option value="builder">builder</option>
            <option value="viewer">viewer</option>
          </select>
        </div>
        <button type="submit" className="btn btn-primary">
          Save profile
        </button>
        {saved && (
          <span className="chip ok" style={{ marginLeft: "0.5rem" }}>
            Saved
          </span>
        )}
      </form>
    </div>
  );
}
