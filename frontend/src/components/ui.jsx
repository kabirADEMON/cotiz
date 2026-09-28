import { useState } from "react";
import { LIBELLES } from "../format";
import Icon from "./Icon";

export function MotDePasse(props) {
  const [visible, setVisible] = useState(false);
  return (
    <div className="mot-de-passe">
      <input {...props} type={visible ? "text" : "password"} />
      <button
        type="button"
        className="bouton-icone"
        onClick={() => setVisible(!visible)}
        aria-label={visible ? "Masquer le mot de passe" : "Afficher le mot de passe"}
        title={visible ? "Masquer" : "Afficher"}
      >
        <Icon name={visible ? "eyeOff" : "eye"} />
      </button>
    </div>
  );
}

export function Logo({ clair = false }) {
  return (
    <span className={`logo ${clair ? "logo-clair" : ""}`}>
      <svg width="28" height="28" viewBox="0 0 32 32" aria-hidden="true">
        <rect width="32" height="32" rx="8" fill="currentColor" className="logo-fond" />
        <circle cx="16" cy="16" r="7.5" fill="none" stroke="#fff" strokeWidth="2.5" strokeDasharray="36 11" />
        <circle cx="23.2" cy="13" r="2.4" fill="#f5c542" />
      </svg>
      Cotiz
    </span>
  );
}

export function Badge({ valeur }) {
  return (
    <span className={`badge badge-${valeur}`}>
      <span className="badge-point" />
      {LIBELLES[valeur] ?? valeur}
    </span>
  );
}

export function Alerte({ message, type = "erreur" }) {
  if (!message) return null;
  const icone = { erreur: "alert", info: "info", succes: "check" }[type];
  return (
    <div className={`alerte alerte-${type}`} role={type === "erreur" ? "alert" : "status"}>
      <Icon name={icone} size={18} />
      <span>{message}</span>
    </div>
  );
}

export function Progression({ valeur, max }) {
  const pourcentage = max ? Math.min(100, Math.round((valeur / max) * 100)) : 0;
  return (
    <div className="progression" role="progressbar" aria-valuenow={pourcentage} aria-valuemin={0} aria-valuemax={100}>
      <div className="progression-barre" style={{ width: `${pourcentage}%` }} />
    </div>
  );
}

export function Avatar({ user, taille = "md" }) {
  const initiales = `${user.prenom[0] ?? ""}${user.nom[0] ?? ""}`.toUpperCase();
  const teinte = [...user.telephone].reduce((s, c) => s + c.charCodeAt(0), 0) % 5;
  return <span className={`avatar avatar-${taille} avatar-teinte-${teinte}`}>{initiales}</span>;
}

export function Personne({ user, detail }) {
  return (
    <div className="personne">
      <Avatar user={user} />
      <div>
        <div className="personne-nom">{user.prenom} {user.nom}</div>
        {detail && <div className="personne-detail">{detail}</div>}
      </div>
    </div>
  );
}

export function Stat({ icone, libelle, valeur, detail }) {
  return (
    <div className="stat">
      <div className="stat-icone"><Icon name={icone} size={20} /></div>
      <div>
        <div className="stat-libelle">{libelle}</div>
        <div className="stat-valeur">{valeur}</div>
        {detail && <div className="stat-detail">{detail}</div>}
      </div>
    </div>
  );
}

export function Vide({ icone, titre, children }) {
  return (
    <div className="vide">
      <div className="vide-icone"><Icon name={icone} size={24} /></div>
      <h3>{titre}</h3>
      {children && <p>{children}</p>}
    </div>
  );
}

export function Modale({ titre, onFermer, children }) {
  return (
    <div className="modale-fond" onMouseDown={(e) => e.target === e.currentTarget && onFermer()}>
      <div className="modale" role="dialog" aria-modal="true" aria-label={titre}>
        <div className="modale-entete">
          <h2>{titre}</h2>
          <button className="bouton-icone" onClick={onFermer} aria-label="Fermer">
            <Icon name="x" />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function Chargement() {
  return (
    <div className="chargement" aria-label="Chargement">
      <span className="spinner" />
    </div>
  );
}

export function EnTete({ titre, sousTitre, children }) {
  return (
    <div className="en-tete">
      <div>
        <h1>{titre}</h1>
        {sousTitre && <p className="en-tete-sous-titre">{sousTitre}</p>}
      </div>
      {children && <div className="en-tete-actions">{children}</div>}
    </div>
  );
}
