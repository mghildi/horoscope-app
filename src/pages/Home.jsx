import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

function Home() {
  const [matches, setMatches] = useState([]);

  useEffect(() => {
    fetch("/matches.json")
      .then((res) => res.json())
      .then((data) => setMatches(data))
      .catch((err) => console.error("Failed to load matches:", err));
  }, []);

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      <h1 className="text-3xl font-bold text-center text-blue-600 mb-6">
        🏏 Today's Matches
      </h1>

      {matches.length === 0 ? (
        <p className="text-center text-red-500">⚠️ No matches available</p>
      ) : (
        <ul className="grid gap-4 max-w-xl mx-auto">
          {matches.map((match) => (
            <li key={match.matchId}>
              <Link
                to={`/match/${match.matchId}`}
                className="block bg-white p-4 shadow rounded hover:bg-blue-50 transition"
              >
                {match.teams}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default Home;
