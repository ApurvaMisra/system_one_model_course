"""Present native answers and probabilities without inventing LLM confidence."""
import pandas as pd


def comparison_tables(records):
    """Return one answer row per interface and one probability column per interface."""
    summaries = {}
    distributions = {}
    for label, record in records.items():
        summary = {'status': record.status, 'error': record.error}
        probabilities = {}
        for name, answer in record.answers.items():
            if record.endpoint == 'responses':
                summary[name] = answer.get('value')
                continue
            for field in ('choice', 'score', 'noul', 'probability'):
                if field in answer:
                    summary[name] = answer[field]
                    break
            distribution = answer.get('probabilities', {})
            if isinstance(distribution, list):
                distribution = {str(item['value']): item['probability'] for item in distribution}
            for option, probability in distribution.items():
                probabilities[(name, str(option))] = probability
            yes_probability = answer.get('noul', answer.get('probability'))
            if yes_probability is not None:
                probabilities[(name, 'yes')] = yes_probability
                probabilities[(name, 'no')] = 1 - yes_probability
        summaries[label] = summary
        distributions[label] = probabilities
    answers = pd.DataFrame.from_dict(summaries, orient='index')
    probabilities = pd.DataFrame(distributions)
    if not probabilities.empty:
        probabilities.index = pd.MultiIndex.from_tuples(probabilities.index, names=['question', 'option'])
    return answers, probabilities
