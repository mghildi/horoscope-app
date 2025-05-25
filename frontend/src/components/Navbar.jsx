import { Link, useLocation } from "react-router-dom";

function Navbar() {
  const { pathname } = useLocation();

  const linkStyle = (path) =>
    `px-4 py-2 font-medium ${
      pathname === path ? "text-blue-600 border-b-2 border-blue-600" : "text-gray-700"
    }`;

  return (
    <nav className="bg-white shadow-md px-6 py-4 flex justify-between items-center">
      <h1 className="text-xl font-bold text-blue-600">My Starter Site</h1>
      <div className="space-x-4">
        <Link to="/" className={linkStyle("/")}>Home</Link>
        <Link to="/about" className={linkStyle("/about")}>About</Link>
        <Link to="/how-it-works" className={linkStyle("/how-it-works")}>How It Works</Link>
        <Link to="/contact" className={linkStyle("/contact")}>Contact</Link>
      </div>
    </nav>
  );
}

export default Navbar;
