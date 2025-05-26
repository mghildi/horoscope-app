import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

function MatchPage() {
  const { matchId } = useParams();
  const [players, setPlayers] = useState([]);

  useEffect(() => {
    fetch(`/leaderboard-${matchId}.json`)
      .then((res) => res.json())
      .then((data) => setPlayers(data))
      .catch((err) => console.error("Failed to load leaderboard:", err));
  }, [matchId]);

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      <h2 className="text-2xl font-bold text-center text-green-700 mb-4">
        Horoscope Leaderboard
      </h2>

      <div className="overflow-x-auto">
        <table className="min-w-full bg-white shadow rounded">
          <thead>
            <tr className="bg-green-100 text-green-900 text-left">
              <th className="px-4 py-2">Player</th>
              <th className="px-4 py-2">Team</th>
              <th className="px-4 py-2">Zodiac</th>
              <th className="px-4 py-2">DOB</th>
              <th className="px-4 py-2">Prediction Scale</th>
            </tr>
          </thead>
          <tbody>
            {players.map((p, idx) => (
              <tr key={idx} className="border-t hover:bg-gray-50">
                <td className="px-4 py-2">{p.Player}</td>
                <td className="px-4 py-2">{p.Team}</td>
                <td className="px-4 py-2">{p.Zodiac}</td>
                <td className="px-4 py-2">{p.DOB}</td>
                <td className="px-4 py-2 text-center font-bold">
                  {p.PredictionScale ?? "N/A"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default MatchPage;
