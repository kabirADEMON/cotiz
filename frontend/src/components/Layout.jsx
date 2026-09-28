import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../AuthContext";
import Icon from "./Icon";
import { Avatar, Logo } from "./ui";

export default function Layout() {
  const { user, deconnexion } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [nonLues, setNonLues] = useState(0);

  useEffect(() => {
    api
      .get("/notifications?non_lues=true")
      .then((liste) => setNonLues(liste.length))
      .catch(() => {});
  }, [location.pathname]);

  function quitter() {
    deconnexion();
    navigate("/connexion");
  }

  const liens = [
    { to: "/", icone: "dashboard", libelle: "Tableau de bord", end: true },
    { to: "/paiements", icone: "wallet", libelle: "Mes paiements" },
    { to: "/notifications", icone: "bell", libelle: "Notifications", compteur: nonLues },
  ];
  if (user.is_admin) liens.push({ to: "/admin", icone: "shield", libelle: "Administration" });

  return (
    <div className="app">
      <aside className="sidebar">
        <NavLink to="/" className="sidebar-logo">
          <Logo />
        </NavLink>
        <nav className="sidebar-nav">
          {liens.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.end} className="nav-lien">
              <Icon name={l.icone} />
              <span>{l.libelle}</span>
              {l.compteur > 0 && <span className="nav-compteur">{l.compteur}</span>}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-user">
          <Avatar user={user} />
          <div className="sidebar-user-info">
            <div className="sidebar-user-nom">{user.prenom} {user.nom}</div>
            <div className="sidebar-user-tel">{user.telephone}</div>
          </div>
          <button className="bouton-icone" onClick={quitter} title="Se déconnecter" aria-label="Se déconnecter">
            <Icon name="logout" />
          </button>
        </div>
      </aside>
      <main className="contenu">
        <Outlet />
      </main>
    </div>
  );
}
