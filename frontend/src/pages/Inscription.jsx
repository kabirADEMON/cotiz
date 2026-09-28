import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../AuthContext";
import AuthLayout from "../components/AuthLayout";
import { Alerte, MotDePasse } from "../components/ui";

export default function Inscription() {
  const { connexion } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ prenom: "", nom: "", telephone: "+229", email: "", password: "" });
  const [erreur, setErreur] = useState(null);
  const [envoi, setEnvoi] = useState(false);

  const champ = (nom) => ({ value: form[nom], onChange: (e) => setForm({ ...form, [nom]: e.target.value }) });

  async function soumettre(e) {
    e.preventDefault();
    setEnvoi(true);
    try {
      const telephone = form.telephone.replace(/\s/g, "");
      await api.post("/auth/register", { ...form, telephone, email: form.email || null });
      await connexion(telephone, form.password);
      navigate("/");
    } catch (err) {
      setErreur(err.message);
    } finally {
      setEnvoi(false);
    }
  }

  return (
    <AuthLayout titre="Créer un compte" sousTitre="Rejoignez ou créez votre première tontine en quelques minutes.">
      <form onSubmit={soumettre}>
        <Alerte message={erreur} />
        <div className="grille-champs">
          <label className="champ">
            <span>Prénom</span>
            <input autoComplete="given-name" {...champ("prenom")} required />
          </label>
          <label className="champ">
            <span>Nom</span>
            <input autoComplete="family-name" {...champ("nom")} required />
          </label>
        </div>
        <label className="champ">
          <span>Numéro de téléphone</span>
          <input type="tel" autoComplete="tel" placeholder="+229 01 97 00 00 00" {...champ("telephone")} required />
        </label>
        <label className="champ">
          <span>Email <em>facultatif</em></span>
          <input type="email" autoComplete="email" {...champ("email")} />
        </label>
        <label className="champ">
          <span>Mot de passe</span>
          <MotDePasse autoComplete="new-password" minLength={8} {...champ("password")} required />
          <small>8 caractères minimum</small>
        </label>
        <button className="bouton bouton-large" disabled={envoi}>
          {envoi ? "Création…" : "Créer mon compte"}
        </button>
      </form>
      <p className="auth-bas">
        Déjà inscrit ? <Link to="/connexion">Se connecter</Link>
      </p>
    </AuthLayout>
  );
}
