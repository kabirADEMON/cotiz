import Icon from "./Icon";
import { Logo } from "./ui";

const ATOUTS = [
  "Calendrier des tours généré automatiquement",
  "Cotisations par Mobile Money ou en espèces",
  "Historique complet, visible par tous les membres",
];

export default function AuthLayout({ titre, sousTitre, children }) {
  return (
    <div className="auth">
      <section className="auth-panneau">
        <Logo clair />
        <div>
          <h2>Vos tontines, gérées en toute transparence.</h2>
          <ul>
            {ATOUTS.map((a) => (
              <li key={a}>
                <Icon name="check" size={18} />
                {a}
              </li>
            ))}
          </ul>
        </div>
        <p className="auth-panneau-pied">
          <Icon name="lock" size={14} /> Paiements sécurisés via FedaPay
        </p>
      </section>
      <section className="auth-formulaire">
        <div className="auth-boite">
          <div className="auth-logo-mobile"><Logo /></div>
          <h1>{titre}</h1>
          <p className="auth-sous-titre">{sousTitre}</p>
          {children}
        </div>
      </section>
    </div>
  );
}
