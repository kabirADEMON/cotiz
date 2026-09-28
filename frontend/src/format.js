export const fcfa = (montant) => `${montant.toLocaleString("fr-FR").replace(/\s/g, " ")} FCFA`;

// "2026-10-01" est interprété en UTC par Date : on force l'heure locale pour ne pas décaler le jour.
const versDate = (valeur) => new Date(/^\d{4}-\d{2}-\d{2}$/.test(valeur) ? `${valeur}T00:00` : valeur);

export const dateCourte = (valeur) =>
  valeur ? versDate(valeur).toLocaleDateString("fr-FR", { day: "numeric", month: "short", year: "numeric" }) : "—";

export const dateHeure = (valeur) =>
  valeur
    ? versDate(valeur).toLocaleString("fr-FR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })
    : "—";

export const nomComplet = (user) => `${user.prenom} ${user.nom}`;

export const PERIODE = { quotidienne: "jour", hebdomadaire: "semaine", mensuelle: "mois" };

export const LIBELLES = {
  quotidienne: "Quotidienne",
  hebdomadaire: "Hebdomadaire",
  mensuelle: "Mensuelle",
  brouillon: "En préparation",
  active: "En cours",
  terminee: "Terminée",
  ouvert: "Ouvert",
  clos: "Versé",
  tresorier: "Trésorier",
  membre: "Membre",
  fedapay: "Mobile Money",
  especes: "Espèces",
  en_attente: "En attente",
  reussi: "Réussi",
  echoue: "Échoué",
};
