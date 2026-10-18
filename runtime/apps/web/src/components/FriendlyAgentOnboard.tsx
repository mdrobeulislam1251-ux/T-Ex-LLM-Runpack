type Props = {
  name?: string;
  title: string;
  message: string;
};

export function FriendlyAgentOnboard({
  name = "Tex",
  title,
  message,
}: Props) {
  return (
    <div className="friendly-agent" role="status">
      <div className="avatar" aria-hidden>
        {name.slice(0, 1)}
      </div>
      <div className="bubble">
        <strong>{title}</strong>
        <p>{message}</p>
      </div>
    </div>
  );
}
