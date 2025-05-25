import { useEffect, useState } from "react";

function Home() {
  const [players, setPlayers] = useState([]);

  useEffect(() => {
    fetch("/leaderboard-v2.json")
      .then((res) => res.json())
      .then((data) => setPlayers(data))
      .catch((err) => console.error("Failed to load leaderboard:", err));
  }, []);

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      <h1 className="text-3xl font-bold text-center text-blue-600 mb-6">
        🏏 Today's Horoscope Leaderboard
      </h1>
      <div className="overflow-x-auto">
        <table className="min-w-full bg-white shadow rounded">
          <thead>
            <tr className="bg-blue-100 text-blue-900 text-left">
              <th className="px-4 py-2">Player</th>
              <th className="px-4 py-2">Team</th>
              <th className="px-4 py-2">Zodiac</th>
              <th className="px-4 py-2">DOB</th>
              <th className="px-4 py-2">Rating</th>
            </tr>
          </thead>
          <tbody>
            {players.map((p, idx) => (
              <tr key={idx} className="border-t hover:bg-gray-50">
                <td className="px-4 py-2">{p.Player}</td>
                <td className="px-4 py-2">{p.Team}</td>
                <td className="px-4 py-2">{p.Zodiac}</td>
                <td className="px-4 py-2">{p.DOB}</td>
                <td className="px-4 py-2 font-bold text-center">{p.Rating ?? "N/A"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default Home;
