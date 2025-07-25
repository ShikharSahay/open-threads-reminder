import type { FC } from "react";
import { useRef, useState } from "react";

export const RequestDemo: FC = () => {

  const [getResults, setGetResults] = useState<string>();
  const [postResults, setPostResults] = useState<string>();
  const inputRef = useRef<HTMLInputElement>(null);

  async function onClickGET() {
    const response = await fetch('/api/sample_get', {
      method: 'GET',
    });

    if (!response.ok) {
      const errMsg = await response.text()
      const message = `Error ${response.status}: ${errMsg}`;
      throw new Error(message);
    }

    const result = await response.text();
    setGetResults(result);
  }

  async function onClickPOST(sample_field: string) {
    const response = await fetch('/api/sample_post', {
      method: 'POST',
      body: JSON.stringify({ sample_field: sample_field }),
    });

    if (!response.ok) {
      const errMsg = await response.text()
      const message = `Error ${response.status}: ${errMsg}`;
      throw new Error(message);
    }

    const result = await response.json();
    setPostResults(JSON.stringify(result));
  }

  return (<div style={{ display: "flex", flexDirection: "column", width: "50%"}}>
    <div>
      Sample GET request
    </div>
    <button
      onClick={() => {
        onClickGET()
          .catch(error => {
            alert("Error executing GET: " + error.message);
          })
      }}
      className="px-4 py-2 rounded-xl border border-neutral-600 text-black bg-white hover:bg-gray-100 transition duration-200">
      GET
    </button>
    <div>
      GET response: {getResults}
    </div>
    <input ref={inputRef} placeholder="sample_field" className="px-4 py-2 rounded-xl border border-neutral-600 text-black bg-white hover:bg-gray-100 transition duration-200"/>
    <button
      onClick={() => {
        onClickPOST(inputRef.current?.value ?? "")
          .catch(error => {
            alert("Error executing POST: " + error.message);
          })
      }}
      className="px-4 py-2 rounded-xl border border-neutral-600 text-black bg-white hover:bg-gray-100 transition duration-200">
      Sample POST request
    </button>
    <div>
      POST response: {postResults}
    </div>
  </div>);

};
