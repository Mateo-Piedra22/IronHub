import { redirect } from 'next/navigation';

// Redirect /gestion to /gestion/usuarios
export default function GestionPage() {
    redirect('/gestion/usuarios');
}

