# parseoeis.py

def sequence_path(seq):
		import pathlib
		if isinstance(seq, str):
				if not seq.startswith("A"):
						seq = int(seq)
				else:
						seq = int(seq[1:])
		else:
				seq = int(seq)
		if not isinstance(seq, int):
				raise TypeError(f"sequence number must be a valid integer in sequence_path(): {repr(seq)}")
		p = pathlib.Path(f"./oeis.org/seq/A{'{:03d}'.format(seq//1000)}/A{'{:06d}'.format(seq)}.seq")

def cleanlineattribs(text):
	import re
	# strip trailing '_name_, date' comments from lines of an oeis seq entry (as text), returning cleaned text
	cleanedlines = []
	namedlines = []
	for line in text.splitlines():
		nameregex = "_[\\w\\s\\.]+_, (Jan|Feb|Mar|Apr|May|Jun|Jul|Sep|Oct|Nov|Dec) \\d\\d? (19|20)\\d\\d"
		linewithnameregex = f"^(.*?) ?(\\(\\* ({nameregex}) \\*\\)|- ({nameregex})|/\\* ({nameregex}) \\*/|// ({nameregex})|# ({nameregex}))$"
		m = re.match(linewithnameregex, line)
		if m != None:
				line = m.group(1)
				name = m.group(2)
		else:
				name = None
		namedlines.append((line, name))
		cleanedlines.append(line)
	return "\n".join(cleanedlines)

# parse some info out of the oeis sequence database entry file format
def process_sequence(seqfile):
		import pathlib, re
		# read file and split into lines in oeis db format (i.e. '%? A###### ...')
		lines = [(fields[0], fields[2]) for fields in [line.strip().split(" ", 2) for line in cleanlineattribs(pathlib.Path(seqfile).read_text()).splitlines()] if len(fields) > 2]
		lused = [False for line in lines]
		def getlines(key, unused_only=False, mark_used=False):
				for linenum in range(0, len(lines)):
						if unused_only and lused[linenum]:
								continue
						if lines[linenum][0] == f"%{key}":
								if mark_used and not lused[linenum]:
										lused[linenum] = True
								yield lines[linenum][1]
		def getkeys(unused_only=False):
				return set([lines[linenum][0].replace("%","") for linenum in range(0, len(lines)) if (not unused_only) or lused[linenum] == False])
		# parse the comma separated list of keywords, i.e. 'frac' etc.
		def getkeywords():
				return [kw.strip() for kw in ",".join(getlines("K", mark_used=False)).split(",")]
		# return true if sequence is part of a fraction
		def isfrac():
				return ('frac' in getkeywords())
		# parse referenced sequences, for references containing 'matching' regex
		def getreference(matching=None):
				for line in getlines("Y", False, False):
						if matching == None or line.find(matching) >= 0:
								for found in re.findall("A[0-9]{6}", line):
										yield found
		# parse three lines of comma separated terms
		def getterms():
				for key in ["S", "T", "U"]:
						for line in getlines(key):
								for field in line.split(","):
										if field.strip() != '':
												yield int(field)
		# split programs section (%o lines) into blocks on lines beginning with '(<language>) ...'
		def getprogs():
				proglines = list(getlines("o", unused_only=False, mark_used=False))
				progs = {}
				curprog = None
				for progline in proglines:
						m = re.match("\\(([^\\)]+)\\) ?(.*)", progline)
						if m == None:
								progtext = progline
						else:
								curprog = m.group(1)
								progtext = m.group(2)
						if curprog != None:
								if not (curprog in progs.keys()):
										progs[curprog] = []
								progs[curprog].append(progtext)
				results = {}
				for progname, proglines in progs.items():
						results[progname] = "\n".join(proglines)
				return results
		# return a dict with a key for each line type, and value a list of the lines with that type
		def getlinesbytype(key, unused_only=False):
				l = list(getlines(key, unused_only=unused_only, mark_used=False))
				return l
		def getalllinesbytype(unused_only=False):
				data = {key: getlinesbytype(key, unused_only=unused_only) for key in getkeys(unused_only=unused_only)}
				return data
		# build a dict of these terms
		seqnum = int(pathlib.Path(seqfile).stem.replace("A", ""))
		seqrefs = list(getreference())
		seqterms = list(getterms())
		seqname = "\n".join(getlines("N"))
		seqcomments = "\n".join(getlines("C"))
		seqformula = list(getlines("F"))
		seqdesc = "\n".join(getlines("D"))
		seqprogs = getprogs()
		seqkeywords = getkeywords()
		seqfrac = {}
		if isfrac():
				numer = list(getreference("numer"))
				denom = list(getreference("denom"))
				if len(numer) > 0:
						seqfrac["numerator"] = numer
				if len(denom) > 0:
						seqfrac["denominator"] = denom
				if len(numer) == 0 and len(denom) == 0:
						#raise RuntimeError(f"seq {seqfile} has frac kw but no numerator or denominator ref entries")
						# frac kw but no clear reference to a numer or denom... assume it is an adjacent sequence? check for unspecified refs to one...
						nextseq = f"A{seqnum+1:06d}"
						prevseq = f"A{seqnum-1:06d}"
						if nextseq in seqrefs:
							seqfrac["denominator"] = [nextseq]
						if prevseq in seqrefs:
							seqfrac["numerator"] = [prevseq]
				if len(seqfrac) == 0:
						raise RuntimeError(f"Seq {seqnum} has 'frac' kw but no clear numerator or denominator reference!")
		return {"seq": seqnum, "terms": seqterms, "name": seqname, "comments": seqcomments, "formula": seqformula, "desc": seqdesc, "programs": seqprogs, "keywords": seqkeywords, "refs": seqrefs, **getalllinesbytype(), **seqfrac}

# process a mirror of the oeis.org website
# i.e all files matching ./oeis.org/seq/A###/A######.txt
def process_sequences():
		import pathlib, tqdm
		sequences = {}
		fraction_numerators = {}
		fraction_denominators = {}

		for seqfile in tqdm.tqdm(sorted(pathlib.Path("./oeis.org/seq").glob("*/*"))):
				#print(f"Reading {seqfile}...")
				seq = seqfile.stem
				try:
						sequence = process_sequence(seqfile)
						sequences[seqfile.stem] = sequence
						if "numerator" in sequence.keys():
								if seq not in fraction_numerators:
										fraction_numerators[seq] = []
								for numerator in sequence["numerator"]:
										fraction_numerators[seq].append(numerator)
						if "denominator" in sequence.keys():
								if seq not in fraction_denominators:
										fraction_denominators[seq] = []
								for denominator in sequence["denominator"]:
										fraction_denominators[seq].append(denominator)
						#yield (seqfile.stem, sequence)
				except Exception as err:
						import traceback
						traceback.print_exc()
						print(f"Warning: got exception {err} (while processing file {repr(seqfile)})")
		return sequences, fraction_numerators, fraction_denominators

from random import choice
import json
from contextlib import contextmanager
@contextmanager
def jsonloutput(filename):
	with open(filename, "wb") as fout:
		class context:
			def __init__(self, fout):
				super().__init__()
				self._fout = fout
			def close(self):
				self._fout.close()
				self._fout = None
			def write(self, obj):
				if self._fout != None:
					return self._fout.write(json.dumps(obj).encode("utf8")+b"\n")
				raise IOError("attempt to write to a closed file")
		yield context(fout)
		fout.close()

if __name__ == "__main__":
		import fractions, tqdm
		seqs, numers, denoms = process_sequences()
		print(f"Done loading, found {len(seqs)} sequences, with {len(numers)}/{len(denoms)} fractions...")
		fracs = {}
		for numer, denoms in numers.items():
			for denom in denoms:
				try:
					fract = dict(seqs[numer].items())
					fract["terms"] = [(fractions.Fraction(term[0], term[1]) if term[1] != 0 else term[0]) for term in zip(fract["terms"], seqs[denom]["terms"])]
					fracs[f"{numer}/{denom}"] = fract
				except Exception as err:
					print(f"Error {err.__class__.__name__} while interpreting {numer}/{denom} as sequence of fractions: {err}")
		nonfracs = {seqnum: seqdat for seqnum, seqdat in seqs.items() if "frac" not in seqdat["keywords"]}

		#print(nonfracs)
		#print(fracs)

		print("\n>>> Writing dataset to oeis.chatml.jsonl...")
		# emit a jsonl file containing conversations
		# (that is compatible with hf datasets)
		with jsonloutput("oeis.chatml.jsonl") as out:
			# emit a question/answer pair in hf chat-template friendly format
			def emitqa(question, answer):
				out.write({"messages":[
					{"role": "user", "content": question},
					{"role": "assistant", "content": answer}
				]})
			# randomly and evenly pick a given number of sequences at random
			def pickshuffledseqs(count, min_terms=10):
				both = list([(key, seq) for key,seq in seqs.items()]) + list([(key, frac) for key, frac in fracs.items()])
				both = list([(key, seq) for key,seq in both if len(seq["terms"]) > min_terms])
				results = []
				while len(results) < count:
					tmp = list(both)
					from random import shuffle
					shuffle(tmp)
					results = results + list(tmp)
				return list(results[:count])
			# pick a random string of consecutive terms from the list, with constraints on length
			def chooseterms(terms, min_count=10, max_count=25):
				from random import choice
				count = choice(list(range(min_count, max_count+1)))
				offset = choice(list(range(0, max(len(terms)-count, 0)+1)))
				return terms[offset:offset+count]
			# counts of each kind of question to generate
			num_seq_nextel = 2000000
			num_seq_missingel = 500000
			num_seq_identify = 2000000
			num_seq_codegen = 100000
			# generate what's the next element? question-answer pairs
			print(f">>> Generating {num_seq_nextel} next-sequence-element question-answer pairs...")
			questions_seq_nextel = [
				"What is the next number in the following sequence?",
				"What is the subsequent term in this numerical series?",
				"Can you determine the next element in this progression?",
				"Find the value that follows in this pattern.",
				"What number logically continues this sequence?",
				"Predict the upcoming number in this series.",
				"What does this sequence of numbers lead to next?",
				"What number comes next in this sequence?",
				"Extrapolate the next term from this sequence.",
				"Given the following sequence, what is the next value?",
				"Continue the following numerical pattern.",
				"What is the next term of this sequence?",
				"If the pattern continues, what will the next number be?",
				"Find the number that comes next in this sequence.",
				"What number comes after this sequence?",
				"Project the next entry in this sequence of numbers."
			]
			for seqnum, seq in tqdm.tqdm(pickshuffledseqs(num_seq_nextel)):
				terms = chooseterms(seq["terms"])
				emitqa(f"{choice(questions_seq_nextel)} {', '.join([str(term) for term in terms[0:-1]])}?", f"{str(terms[-1])}")

			# generate sequence identification question-answer pairs
			print(f">>> Generating {num_seq_identify} sequence identification question-answer pairs...")
			questions_seq_identify = [
				"Describe the following sequence of numbers?",
				"Provide a description of the pattern in this number sequence.",
				"What is the rule that generates these numbers?",
				"Explain the logic behind the following sequence.",
				"How would you define the relationship between the terms in this series?",
				"Characterize the mathematical principle of this progression.",
				"What is the formula for the nth term of this sequence?",
				"Can you identify the following sequence?",
				"Describe the method used to create this sequence of numbers.",
				"What is the underlying algorithm for this numerical pattern?",
				"Uncover the rule governing the sequence.",
				"Explain how to generate the terms in this series.",
				"What properties does this number sequence have?",
				"Provide a closed-form expression for this sequence.",
				"What is the recurrence relation for this sequence?",
				"How are the numbers in this sequence related to each other?"
			]
			for seqnum, seq in tqdm.tqdm(pickshuffledseqs(num_seq_identify)):
				terms = chooseterms(seq["terms"])
				emitqa(f"{choice(questions_seq_identify)} {', '.join([str(term) for term in terms])}?", f"{seq['name']}")

			print()
			print(">>> Done generating dataset!")
'''
### Category 3: Write a program to generate the following sequence in <language>?

"In `<language>`, create a program that outputs the given number series.
"Develop a `<language>` script to produce the terms of this sequence.
"Code a function in `<language>` that generates this numerical pattern.
"Construct a program in `<language>` to replicate the following sequence.
"Write the `<language>` code necessary to generate this series of numbers.
"Please provide a `<language>` implementation that can generate this sequence.
"Generate this sequence programmatically using `<language>`.
"Can you write a snippet in `<language>` that produces this sequence?
"I need a `<language>` program to generate the first `n` terms of this sequence.
"How would you code the generation of this sequence in `<language>`?
"Produce a `<language>` algorithm to create the following numerical series.
"Translate the logic of this sequence into `<language>` code.
"Write a generator function in `<language>` for this sequence.
"Show me how to create this sequence with a loop in `<language>`.
"Using `<language>`, write a program that prints the numbers in this sequence.
'''
