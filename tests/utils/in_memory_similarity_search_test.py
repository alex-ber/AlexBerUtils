import logging
import pytest

try:
    from alexber.utils.in_memory_similarity_search import SimpleEmbeddings, find_most_similar
except ImportError:
    pass

logger = logging.getLogger(__name__)


@pytest.fixture(scope='module')
@pytest.mark.np
def embeddings():
    return SimpleEmbeddings()

@pytest.mark.np
@pytest.mark.parametrize(
    'question, r, a0, a1, expected_idx',

    [
        ("Who was the top goal scorer in the Premier League last season?",
         'According to the given chat history, the top goal scorer in the Premier League last season was Harry Kane, with 23 goals.',

         # 0.9682
         "I don't know who the top goal scorer in the Premier League last season was.",
         # 0.9786
         "The top goal scorer in the Premier League last season was Harry Kane, with 23 goals.",
         1),

        ("Which team won the UEFA Champions League two years ago?",
         'Based on the provided chat history, the team that won the UEFA Champions League two years ago was Bayern Munich.',

         #0.9826
         'The team that won the UEFA Champions League two years ago was Bayern Munich.',
         #0.9592
         "I don't know which team won the UEFA Champions League two years ago.",
         0),


        ("Which country hosted the FIFA World Cup four years ago?",
         'Surveys indicate that 60% of soccer fans believe Lionel Messi is the greatest player of all time.',

         #0.9886
         "60% of soccer fans believe Lionel Messi is the greatest player of all time",
         #0.9802
         "I don't know what percentage of soccer fans believe Lionel Messi is the greatest player of all time.",
         0),

        ("Who is known as the 'King of Football'?",
         'Pelé is known as the "King of Football".',

         #0.9374
         'The "King of Football" is Pele.',
         #0.9045
         'The "King of Football" is Maradona, no, sorry, Pele.',
         0),




        ("Who was named the best goalkeeper in the world last year?",
        'According to sports analysts, the best goalkeeper in the world last year was Manuel Neuer.',

          #0.9571
         'The best goalkeeper in the world last year was Manuel Neuer.',
          #0.9488,
          "I don't know who was named the best goalkeeper in the world last year.",
         0),

        ("What is the most watched soccer match in history?",
         'Records indicate that the most watched soccer match in history is the 2014 FIFA World Cup final between Germany and Argentina',

         #0.9365
         "I don't know what the most watched soccer match in history is.",
         #0.9918
         "The most watched soccer match in history is the 2014 FIFA World Cup final between Germany and Argentina.",
         1),

        ("Which player has the most assists in La Liga history?",
         'Statistics show that the player with the most assists in La Liga history is Lionel Messi.',

         #0.9786
         'The player with the most assists in La Liga history is Lionel Messi.',
         #0.9584
         "I don't know which player has the most assists in La Liga history.",
         0),

        ("What percentage of soccer fans prefer watching club football over international football?",
         'Polls reveal that 70% of soccer fans prefer watching club football over international football.',

         #0.9733
         "I don't know what percentage of soccer fans prefer watching club football over international football.",
         #0.9890
         "70% of soccer fans prefer watching club football over international football",
         1),

        ("Which team has won the most Serie A titles?",
         'Historical data shows that the team that has won the most Serie A titles is Juventus.',

         #0.9764
         'The team that has won the most Serie A titles is Juventus.',
         #0.9380
         "I don't know which team has won the most Serie A titles.",
         0),

        ("Who was awarded the Ballon d'Or last year?",
         "Reports confirm that the player awarded the Ballon d'Or last year was Robert Lewandowski.",

         #0.9403
         "I don't know who was awarded the Ballon d'Or last year.",
         #0.9768
         "The player awarded the Ballon d'Or last year was Robert Lewandowski.",
         1),
    ]
)
def test_find_most_similar(request, embeddings, question, r, a0, a1, expected_idx):
    logger.info(f'{request._pyfuncitem.name}()')

    idx, restored_answer = find_most_similar(embeddings, r, a0, a1)
    logger.info(f'Restored answer a{idx} is {restored_answer}')
    pytest.assume(expected_idx == idx)


if __name__ == "__main__":
    pytest.main([__file__])
