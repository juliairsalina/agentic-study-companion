const { useMemo, useState, useRef } = React;

const BACKEND_BASE = window.APP_CONFIG?.BACKEND_BASE || "http://127.0.0.1:8000";

function App() {
  const [page, setPage] = useState("upload"); // upload | learn | results

  const [pdfFile, setPdfFile] = useState(null);
  const [instruction, setInstruction] = useState("");

  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState("No file uploaded yet.");

  const [summary, setSummary] = useState("");
  const [topics, setTopics] = useState([]);
  const [questions, setQuestions] = useState([]);

  const [currentIndex, setCurrentIndex] = useState(0);
  const [showKeywords, setShowKeywords] = useState(false);

  const [isRecording, setIsRecording] = useState(false);
  const [listeningText, setListeningText] = useState("");
  const [manualTranscript, setManualTranscript] = useState("");

  const [answers, setAnswers] = useState({});
  const [evaluations, setEvaluations] = useState([]);
  const [workflowDecisions, setWorkflowDecisions] = useState([]);

  const [oldSessions, setOldSessions] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem("yapping_sessions") || "[]");
    } catch {
      return [];
    }
  });

  const speechRecognizerRef = useRef(null);
  const finalTranscriptRef = useRef("");

  const currentQuestion = questions[currentIndex];

  const retryQuestions = useMemo(() => {
    const retryIds = workflowDecisions
      .filter((decision) => decision.action === "hint_retry")
      .map((decision) => decision.questionId);

    return questions.filter((question) => retryIds.includes(question.id));
  }, [questions, workflowDecisions]);

  function saveSessionToLocalStorage(sessionData) {
    const newSession = {
      id: `session-${Date.now()}`,
      createdAt: new Date().toLocaleString(),
      filename: sessionData.filename || "uploaded.pdf",
      summary: sessionData.summary || "",
      topics: sessionData.topics || [],
      questions: sessionData.questions || []
    };

    const updated = [newSession, ...oldSessions].slice(0, 8);
    setOldSessions(updated);
    localStorage.setItem("yapping_sessions", JSON.stringify(updated));
  }

  async function handleUpload() {
    if (!pdfFile) {
      setUploadStatus("Please choose a PDF file first.");
      return;
    }

    if (!pdfFile.name.toLowerCase().endsWith(".pdf")) {
      setUploadStatus("Only PDF files are allowed.");
      return;
    }

    setIsUploading(true);
    setUploadStatus("Uploading PDF and calling ContentAgent...");

    const formData = new FormData();
    formData.append("pdf", pdfFile);
    formData.append("instruction", instruction || "");

    try {
      const response = await fetch(`${BACKEND_BASE}/upload/`, {
        method: "POST",
        body: formData
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || "Upload failed.");
      }

      const returnedQuestions = Array.isArray(result.questions) ? result.questions : [];
      const returnedTopics = Array.isArray(result.topics) ? result.topics : [];

      setSummary(result.summary || "");
      setTopics(returnedTopics);
      setQuestions(returnedQuestions);
      setCurrentIndex(0);
      setShowKeywords(false);
      setEvaluations([]);
      setWorkflowDecisions([]);
      setAnswers({});
      setManualTranscript("");
      setListeningText("");

      setUploadStatus(`Uploaded successfully: ${result.filename || pdfFile.name}`);

      saveSessionToLocalStorage({
        filename: result.filename || pdfFile.name,
        summary: result.summary || "",
        topics: returnedTopics,
        questions: returnedQuestions
      });
    } catch (error) {
      console.error(error);
      setUploadStatus(`Error: ${error.message}`);
    } finally {
      setIsUploading(false);
    }
  }

  function resetAll() {
    setPage("upload");
    setPdfFile(null);
    setInstruction("");
    setUploadStatus("No file uploaded yet.");
    setSummary("");
    setTopics([]);
    setQuestions([]);
    setCurrentIndex(0);
    setShowKeywords(false);
    setIsRecording(false);
    setListeningText("");
    setManualTranscript("");
    setAnswers({});
    setEvaluations([]);
    setWorkflowDecisions([]);
  }

  function goNextQuestion() {
    setShowKeywords(false);
    setManualTranscript("");
    setListeningText("");

    if (currentIndex < questions.length - 1) {
      setCurrentIndex(currentIndex + 1);
    }
  }

  function goPrevQuestion() {
    setShowKeywords(false);
    setManualTranscript("");
    setListeningText("");

    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
    }
  }

  function createSpeechRecognizer() {
    if (!window.SpeechSDK) {
      throw new Error("Azure Speech SDK is not loaded.");
    }

    const speechKey = window.APP_CONFIG?.AZURE_SPEECH_KEY || "";
    const speechRegion = window.APP_CONFIG?.AZURE_SPEECH_REGION || "";

    if (!speechKey || !speechRegion) {
      throw new Error(
        "Azure Speech key/region is missing. For now, type your transcript manually in the textbox."
      );
    }

    const speechConfig = SpeechSDK.SpeechConfig.fromSubscription(speechKey, speechRegion);
    speechConfig.speechRecognitionLanguage = "en-US";

    const audioConfig = SpeechSDK.AudioConfig.fromDefaultMicrophoneInput();
    return new SpeechSDK.SpeechRecognizer(speechConfig, audioConfig);
  }

  function startRecording() {
    if (!currentQuestion) return;

    try {
      finalTranscriptRef.current = "";
      setListeningText("agent is listening to your yap...");
      setManualTranscript("");
      setIsRecording(true);

      const recognizer = createSpeechRecognizer();
      speechRecognizerRef.current = recognizer;

      recognizer.recognizing = (_, event) => {
        const partial = event.result?.text || "";
        if (partial) {
          setListeningText(partial);
        }
      };

      recognizer.recognized = (_, event) => {
        const text = event.result?.text || "";
        if (text) {
          finalTranscriptRef.current += ` ${text}`;
          setManualTranscript(finalTranscriptRef.current.trim());
        }
      };

      recognizer.canceled = (_, event) => {
        console.error("Speech canceled:", event);
        setListeningText("Speech recognition stopped or failed.");
        setIsRecording(false);
      };

      recognizer.startContinuousRecognitionAsync(
        () => console.log("Recording started"),
        (error) => {
          console.error(error);
          setListeningText("Could not start recording. You can type your transcript manually.");
          setIsRecording(false);
        }
      );
    } catch (error) {
      console.error(error);
      setListeningText(error.message);
      setIsRecording(false);
    }
  }

  function stopRecording() {
    const recognizer = speechRecognizerRef.current;

    setIsRecording(false);
    setListeningText("Recording stopped.");

    if (!recognizer) return;

    recognizer.stopContinuousRecognitionAsync(
      () => {
        recognizer.close();
        speechRecognizerRef.current = null;
      },
      (error) => {
        console.error(error);
        setListeningText("Could not stop recording correctly.");
      }
    );
  }

  async function evaluateCurrentAnswer() {
    if (!currentQuestion) return;

    const transcript = manualTranscript.trim();

    if (!transcript) {
      alert("Please record or type your answer first.");
      return;
    }

    setAnswers((previous) => ({
      ...previous,
      [currentQuestion.id]: transcript
    }));

    const coachPayload = {
      questionId: currentQuestion.id,
      topic: currentQuestion.topic,
      question: currentQuestion.question,
      transcript,
      idealAnswer: currentQuestion.idealAnswer,
      keywords: currentQuestion.keywords || [],
      sourceChunkIds: currentQuestion.sourceChunkIds || []
    };

    try {
      const coachResponse = await fetch(`${BACKEND_BASE}/evaluate/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(coachPayload)
      });

      const coachResult = await coachResponse.json();

      if (!coachResponse.ok) {
        throw new Error(coachResult.detail || "Evaluation failed.");
      }

      const workflowPayload = {
        question: currentQuestion,
        coachResult
      };

      const workflowResponse = await fetch(`${BACKEND_BASE}/workflow/decide`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(workflowPayload)
      });

      const workflowResult = await workflowResponse.json();

      if (!workflowResponse.ok) {
        throw new Error(workflowResult.detail || "Workflow decision failed.");
      }

      const decision = workflowResult.decision || workflowResult;

      setEvaluations((previous) => {
        const withoutCurrent = previous.filter((item) => item.questionId !== currentQuestion.id);
        return [...withoutCurrent, coachResult];
      });

      setWorkflowDecisions((previous) => {
        const withoutCurrent = previous.filter((item) => item.questionId !== currentQuestion.id);
        return [...withoutCurrent, decision];
      });

      if (currentIndex < questions.length - 1) {
        goNextQuestion();
      } else {
        setPage("results");
      }
    } catch (error) {
      console.error(error);
      alert(error.message);
    }
  }

  function startRetrySession() {
    if (retryQuestions.length === 0) {
      alert("No hint_retry cards found.");
      return;
    }

    setQuestions(retryQuestions);
    setCurrentIndex(0);
    setShowKeywords(true);
    setManualTranscript("");
    setListeningText("");
    setPage("learn");
  }

  return (
    <div className="app-shell">
      {page === "upload" && (
        <UploadPage
          pdfFile={pdfFile}
          setPdfFile={setPdfFile}
          instruction={instruction}
          setInstruction={setInstruction}
          isUploading={isUploading}
          uploadStatus={uploadStatus}
          handleUpload={handleUpload}
          summary={summary}
          topics={topics}
          questions={questions}
          setPage={setPage}
          oldSessions={oldSessions}
          resetAll={resetAll}
        />
      )}

      {page === "learn" && (
        <LearnPage
          currentQuestion={currentQuestion}
          currentIndex={currentIndex}
          totalQuestions={questions.length}
          showKeywords={showKeywords}
          setShowKeywords={setShowKeywords}
          goNextQuestion={goNextQuestion}
          goPrevQuestion={goPrevQuestion}
          isRecording={isRecording}
          startRecording={startRecording}
          stopRecording={stopRecording}
          listeningText={listeningText}
          manualTranscript={manualTranscript}
          setManualTranscript={setManualTranscript}
          evaluateCurrentAnswer={evaluateCurrentAnswer}
          setPage={setPage}
        />
      )}

      {page === "results" && (
        <ResultsPage
          questions={questions}
          answers={answers}
          evaluations={evaluations}
          workflowDecisions={workflowDecisions}
          retryQuestions={retryQuestions}
          startRetrySession={startRetrySession}
          resetAll={resetAll}
        />
      )}
    </div>
  );
}

function UploadPage({
  pdfFile,
  setPdfFile,
  instruction,
  setInstruction,
  isUploading,
  uploadStatus,
  handleUpload,
  summary,
  topics,
  questions,
  setPage,
  oldSessions,
  resetAll
}) {
  return (
    <main className="upload-page">
      <section className="hero-card glass-card">
        <div className="mini-pill">Agentic AI Study Companion</div>

        <h1>Yapping Study Buddy</h1>

        <p className="hero-subtitle">
          Upload a lecture PDF, generate flashcards, answer by speaking, and let your agents decide
          whether to advance, retry with hint, or reveal and move.
        </p>

        <div className="upload-box">
          <label className="file-drop">
            <input
              type="file"
              accept=".pdf"
              onChange={(event) => setPdfFile(event.target.files[0] || null)}
            />

            <span className="file-main-text">
              {pdfFile ? pdfFile.name : "Choose your PDF"}
            </span>

            <span className="file-sub-text">
              PDF only. Your backend will extract text and call ContentAgent.
            </span>
          </label>

          <div className="instruction-row">
            <input
              value={instruction}
              onChange={(event) => setInstruction(event.target.value)}
              placeholder="Write optional instruction: focus on exam-style questions..."
            />

            <button onClick={handleUpload} disabled={isUploading}>
              {isUploading ? "Processing..." : "Upload"}
            </button>
          </div>

          <p className="status-text">{uploadStatus}</p>
        </div>

        <section className="old-session-box">
          <div className="section-title-row">
            <h3>Old flashcards</h3>
            <span>temporary localStorage</span>
          </div>

          {oldSessions.length === 0 ? (
            <p className="muted-text">
              No old flashcards yet. Later this section can call Cosmos DB through the backend.
            </p>
          ) : (
            <div className="old-session-list">
              {oldSessions.map((session) => (
                <div className="old-session-item" key={session.id}>
                  <strong>{session.filename}</strong>
                  <small>{session.createdAt}</small>
                  <span>{session.questions?.length || 0} cards</span>
                </div>
              ))}
            </div>
          )}
        </section>

        {summary && (
          <section className="summary-popup glass-card">
            <div className="section-title-row">
              <h2>AI Summary</h2>
              <span>{questions.length} questions</span>
            </div>

            <p>{summary}</p>

            <h3>Topic summary</h3>

            <div className="topic-list">
              {topics.map((topic) => (
                <span key={topic}>{topic}</span>
              ))}
            </div>

            <div className="button-row center">
              <button
                className="primary-btn"
                disabled={questions.length === 0}
                onClick={() => setPage("learn")}
              >
                Start learning by yapping
              </button>

              <button className="secondary-btn" onClick={resetAll}>
                Reset
              </button>
            </div>
          </section>
        )}
      </section>
    </main>
  );
}

function LearnPage({
  currentQuestion,
  currentIndex,
  totalQuestions,
  showKeywords,
  setShowKeywords,
  goNextQuestion,
  goPrevQuestion,
  isRecording,
  startRecording,
  stopRecording,
  listeningText,
  manualTranscript,
  setManualTranscript,
  evaluateCurrentAnswer,
  setPage
}) {
  if (!currentQuestion) {
    return (
      <main className="center-page">
        <div className="glass-card empty-card">
          <h2>No questions available</h2>
          <button onClick={() => setPage("upload")}>Back to upload</button>
        </div>
      </main>
    );
  }

  return (
    <main className="learn-page">
      <section className="learn-header">
        <div>
          <p className="mini-pill">Flashcard learning</p>
          <h1>Answer by yapping</h1>
        </div>

        <button className="secondary-btn" onClick={() => setPage("results")}>
          View results
        </button>
      </section>

      <section className="carousel-area">
        <button className="carousel-btn" onClick={goPrevQuestion} disabled={currentIndex === 0}>
          ‹
        </button>

        <article className="question-card glass-card">
          <div className="card-top-row">
            <span className="topic-badge">{currentQuestion.topic || "General"}</span>
            <span className="counter-badge">
              {currentIndex + 1} / {totalQuestions}
            </span>
          </div>

          <h2>{currentQuestion.question}</h2>

          <button
            className="hint-btn"
            onClick={() => setShowKeywords(!showKeywords)}
          >
            {showKeywords ? "Hide hint keywords" : "Show hint keywords"}
          </button>

          {showKeywords && (
            <div className="keyword-tags">
              {(currentQuestion.keywords || []).map((keyword, index) => (
                <span className={`keyword-tag tag-${index % 5}`} key={keyword}>
                  {keyword}
                </span>
              ))}
            </div>
          )}

          <div className="record-panel">
            <div className="record-buttons">
              <button
                className="record-btn"
                onClick={startRecording}
                disabled={isRecording}
              >
                🎙 Start recording
              </button>

              <button
                className="stop-btn"
                onClick={stopRecording}
                disabled={!isRecording}
              >
                ⏹ Stop recording
              </button>
            </div>

            <p className="listening-placeholder">
              {listeningText || "agent is waiting for your yap..."}
            </p>

            <textarea
              value={manualTranscript}
              onChange={(event) => setManualTranscript(event.target.value)}
              placeholder="Transcript will appear here. If Azure Speech is not connected yet, type your answer manually for testing."
            />
          </div>

          <div className="button-row">
            <button className="primary-btn" onClick={evaluateCurrentAnswer}>
              Submit answer to CoachAgent
            </button>
          </div>
        </article>

        <button
          className="carousel-btn"
          onClick={goNextQuestion}
          disabled={currentIndex === totalQuestions - 1}
        >
          ›
        </button>
      </section>
    </main>
  );
}

function ResultsPage({
  questions,
  answers,
  evaluations,
  workflowDecisions,
  retryQuestions,
  startRetrySession,
  resetAll
}) {
  function getEvaluation(questionId) {
    return evaluations.find((item) => item.questionId === questionId);
  }

  function getDecision(questionId) {
    return workflowDecisions.find((item) => item.questionId === questionId);
  }

  return (
    <main className="results-page">
      <section className="results-header">
        <div>
          <p className="mini-pill">Evaluation Agent Result</p>
          <h1>Study session review</h1>
        </div>

        <div className="button-row">
          <button className="secondary-btn" onClick={resetAll}>
            New upload
          </button>

          <button
            className="primary-btn"
            onClick={startRetrySession}
            disabled={retryQuestions.length === 0}
          >
            Retry hint cards only ({retryQuestions.length})
          </button>
        </div>
      </section>

      <section className="result-list">
        {questions.map((question) => {
          const evaluation = getEvaluation(question.id);
          const decision = getDecision(question.id);

          return (
            <article className="result-card glass-card" key={question.id}>
              <div className="card-top-row">
                <span className="topic-badge">{question.topic || "General"}</span>
                <span className={`decision-badge ${decision?.action || "waiting"}`}>
                  {decision?.action || "not evaluated"}
                </span>
              </div>

              <h2>{question.question}</h2>

              <div className="result-grid">
                <div>
                  <h3>Transcribed answer</h3>
                  <p>{answers[question.id] || "No answer submitted."}</p>
                </div>

                <div>
                  <h3>CoachAgent evaluation</h3>
                  <pre>{JSON.stringify(evaluation || {}, null, 2)}</pre>
                </div>

                <div>
                  <h3>WorkflowAgent decision</h3>
                  <pre>{JSON.stringify(decision || {}, null, 2)}</pre>
                </div>
              </div>
            </article>
          );
        })}
      </section>
    </main>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);