// Fake data with the same shape as the real POST /analyze response.
// It lets us build the screen before connecting to the backend in Milestone 3.
export const sampleResult = {
  total_tokens: 1000,
  unique_lemmas: 17,
  lemmas: [
    { lemma: 'i', count: 113, rank: 1, pos: 'CCONJ', forms: ['i'], example: 'Był cichy i spokojny.', is_stopword: true },
    { lemma: 'się', count: 101, rank: 2, pos: 'PRON', forms: ['się'], example: 'Był zawsze głęboko zamyślony i posuwał się z wolna.', is_stopword: true },
    { lemma: 'on', count: 96, rank: 3, pos: 'PRON', forms: ['jej', 'nim', 'jego', 'niej', 'mu'], example: 'Toż samo ulica Miodowa pomyśleć by mogła o nim.', is_stopword: true },
    { lemma: 'w', count: 91, rank: 4, pos: 'ADP', forms: ['w', 'we'], example: 'Spotkał jegomościa w pewnym wieku.', is_stopword: true },
    { lemma: 'nie', count: 79, rank: 5, pos: 'PART', forms: ['nie'], example: 'Czasu im nie poświęcał.', is_stopword: true },
    { lemma: 'na', count: 75, rank: 6, pos: 'ADP', forms: ['na'], example: 'Gdy mecenas usłyszał na ulicy katarynkę, przyśpieszał kroku.', is_stopword: true },
    { lemma: 'być', count: 70, rank: 7, pos: 'AUX', forms: ['był', 'było', 'jest', 'była', 'były'], example: 'Był zawsze głęboko zamyślony.', is_stopword: true },
    { lemma: 'pan', count: 39, rank: 8, pos: 'NOUN', forms: ['pan', 'pana', 'panie', 'panu'], example: 'Pan Tomasz wyszedł z domu.', is_stopword: true },
    { lemma: 'mecenas', count: 33, rank: 9, pos: 'NOUN', forms: ['mecenas', 'mecenasa', 'mecenasem', 'mecenasowi'], example: 'Gdy został mecenasem, czoło urosło mu aż do ciemienia.', is_stopword: false },
    { lemma: 'widzieć', count: 22, rank: 10, pos: 'VERB', forms: ['widzi', 'widzę', 'widząc', 'widzieć', 'widział'], example: 'Nie widział nikogo na ulicy.', is_stopword: false },
    { lemma: 'dziewczynka', count: 21, rank: 11, pos: 'NOUN', forms: ['dziewczynka', 'dziewczynką', 'dziewczynce', 'dziewczynki'], example: 'Do lokalu sprowadziły się dwie panie z małą dziewczynką.', is_stopword: false },
    { lemma: 'dzień', count: 19, rank: 12, pos: 'NOUN', forms: ['dzień', 'dnia', 'dni', 'dniach'], example: 'Na ulicy Miodowej co dzień można było go spotkać.', is_stopword: false },
    { lemma: 'dom', count: 14, rank: 13, pos: 'NOUN', forms: ['domu', 'dom', 'domem', 'domami'], example: 'Wieczorem wrócił do domu.', is_stopword: false },
    { lemma: 'mówić', count: 14, rank: 14, pos: 'VERB', forms: ['mówił', 'mówiła', 'mówiąc', 'mówisz', 'mówiły'], example: 'Jeżeli podobało mu się coś, mówił, że jest to wcale ładne.', is_stopword: false },
    { lemma: 'katarynka', count: 12, rank: 15, pos: 'NOUN', forms: ['katarynka', 'katarynki', 'katarynkę', 'katarynek'], example: 'Oto — nienawidził kataryniarzy i katarynek.', is_stopword: false },
    { lemma: 'okno', count: 12, rank: 16, pos: 'NOUN', forms: ['okna', 'oknie', 'okien', 'oknem'], example: 'Ktoś wysłał mu pod okna kataryniarza.', is_stopword: false },
    { lemma: 'piękny', count: 8, rank: 17, pos: 'ADJ', forms: ['piękne', 'pięknych', 'piękna'], example: 'Sztuki piękne robiły na nim wrażenie.', is_stopword: false },
  ],
}
